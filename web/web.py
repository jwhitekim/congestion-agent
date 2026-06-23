import json
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT_DIR / "agent_system"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import domains
from agent import ClaudeAgent, DEFAULT_MODEL, MODEL_ALIASES

UPLOAD_DIR = ROOT_DIR / "uploads"
RESULTS_DIR = ROOT_DIR / "results"

app = Flask(__name__, template_folder="frontend", static_folder="frontend", static_url_path="")


def _safe_name(filename: str) -> str:
    keep = []
    for char in Path(filename).name:
        keep.append(char if char.isalnum() or char in "._-" else "_")
    cleaned = "".join(keep).strip("._")
    return cleaned or "video.mp4"


def _analyze(video_path: Path, domain_name: str, model_alias: str, interval_sec: float) -> dict:
    domain_config = domains.load(domain_name)
    agent = ClaudeAgent(
        system_prompt=domain_config["system_prompt"],
        tools=domain_config["tools"],
        model=MODEL_ALIASES[model_alias],
    )

    # 데모 웹은 첫 구간을 바로 분석한다. 도구 호출 여부는 ClaudeAgent 내부에서 두뇌가 결정한다.
    result = agent.run(str(video_path), start_sec=0.0, end_sec=interval_sec)
    return {
        "domain": domain_name,
        "model": model_alias,
        "interval_sec": interval_sec,
        "segments": [{"segment_index": 1, "segment": {"start_sec": 0.0, "end_sec": interval_sec}, "result": result}],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    uploaded = request.files.get("video")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "video file is required"}), 400

    model_alias = request.form.get("model", DEFAULT_MODEL)
    domain_name = request.form.get("domain", "congestion")
    interval_sec = float(request.form.get("interval", "5") or 5)
    if model_alias not in MODEL_ALIASES:
        return jsonify({"error": f"unsupported model alias: {model_alias}"}), 400
    if interval_sec <= 0:
        return jsonify({"error": "interval must be greater than 0"}), 400

    UPLOAD_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    upload_id = uuid.uuid4().hex[:12]
    video_path = UPLOAD_DIR / f"{upload_id}_{_safe_name(uploaded.filename)}"
    uploaded.save(video_path)

    try:
        payload = _analyze(video_path, domain_name, model_alias, interval_sec)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    result_path = RESULTS_DIR / f"{upload_id}.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["saved_result"] = str(result_path.relative_to(ROOT_DIR))
    payload["uploaded_video"] = str(video_path.relative_to(ROOT_DIR))
    return jsonify(payload)


if __name__ == "__main__":
    load_dotenv(ROOT_DIR / ".env")
    app.run(host="127.0.0.1", port=8000, debug=True)
