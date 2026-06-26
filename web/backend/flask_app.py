import json
import logging
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from web.settings import *
from web.backend.analyzer import analyze_video
from agent_system.agent import DEFAULT_MODEL, MODEL_ALIASES
from agent_system.utils.custom_logger import GetLogger

load_dotenv(ROOT_DIR / ".env")
logger = GetLogger("web", str(LOGS_DIR / "web.log"))
app = Flask(__name__, template_folder=STATIC_DIR, static_folder=STATIC_DIR, static_url_path="/public")


for _handler in logger.handlers:
    app.logger.addHandler(_handler)
    logging.getLogger("werkzeug").addHandler(_handler)
app.logger.setLevel(logging.DEBUG)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    uploaded = request.files.get("video")
    if uploaded is None or not uploaded.filename:
        logger.warning("Request rejected: video file missing")
        return jsonify({"error": "video file is required"}), 400

    model_alias = request.form.get("model", DEFAULT_MODEL)
    domain_name = request.form.get("domain", "congestion")
    interval_sec = float(request.form.get("interval", "5") or 5)

    if model_alias not in MODEL_ALIASES:
        logger.warning("Request rejected: unsupported model alias=%s", model_alias)
        return jsonify({"error": f"unsupported model alias: {model_alias}"}), 400
    if interval_sec <= 0:
        logger.warning("Request rejected: invalid interval=%s", interval_sec)
        return jsonify({"error": "interval must be greater than 0"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    upload_id = uuid.uuid4().hex[:12]
    video_path = UPLOAD_DIR / f"{upload_id}_{uploaded.filename}"
    uploaded.save(video_path)
    logger.info(
        "Request received: id=%s file=%s model=%s domain=%s interval=%s",
        upload_id, uploaded.filename, model_alias, domain_name, interval_sec,
    )

    try:
        payload = analyze_video(video_path, domain_name, model_alias, interval_sec)
    except Exception as exc:
        logger.exception("Analysis failed: id=%s", upload_id)
        return jsonify({"error": str(exc)}), 500

    result_path = RESULTS_DIR / f"{upload_id}.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Result saved: %s", result_path)

    payload["saved_result"] = str(result_path.relative_to(ROOT_DIR))
    payload["uploaded_video"] = str(video_path.relative_to(ROOT_DIR))
    return jsonify(payload)


