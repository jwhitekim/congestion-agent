from pathlib import Path

from web.settings import LOGS_DIR
from web.backend.utils import _build_segments

import agent_system.domains as domains
from agent_system.agent import ClaudeAgent, MODEL_ALIASES
from agent_system.utils.video import build_vision_content, load_video_info
from agent_system.utils.custom_logger import GetLogger


logger = GetLogger("web", str(LOGS_DIR / "web.log"))


def analyze_video(video_path: Path, domain_name: str, model_alias: str, interval_sec: float) -> dict:
    domain_config = domains.load(domain_name)
    agent = ClaudeAgent(
        system_prompt=domain_config["system_prompt"],
        tools=domain_config["tools"],
        model=MODEL_ALIASES[model_alias],
    )

    video_info = load_video_info(video_path)
    segments = _build_segments(video_info["duration_sec"], interval_sec)
    logger.info(
        "Analysis start: video=%s domain=%s model=%s interval=%ss segments=%d",
        video_path.name, domain_name, model_alias, interval_sec, len(segments),
    )

    results = []
    for index, segment in enumerate(segments, start=1):
        start_sec = segment["start_sec"]
        end_sec = segment["end_sec"]
        logger.info("Segment %d/%d: %ss~%ss", index, len(segments), start_sec, end_sec)
        try:
            content = build_vision_content(str(video_path), start_sec, end_sec)
            result = agent.run(content)
            result["frame_timestamp"] = start_sec  # 어느 프레임인지 — 시스템이 추가
            record = {"segment_index": index, "segment": segment, "result": result}
            logger.info(
                "Segment %d result: people=%s level=%s action=%s tool_called=%s",
                index,
                result.get("total_people"),
                result.get("congestion_level"),
                result.get("action"),
                result.get("tool_called"),
            )
        except Exception as exc:
            logger.exception("Segment %d analysis failed", index)
            record = {"segment_index": index, "segment": segment, "error": str(exc)}
        results.append(record)

    return {
        "video": str(video_path),
        "domain": domain_name,
        "model": model_alias,
        "interval_sec": interval_sec,
        "video_info": video_info,
        "segments": results,
    }

