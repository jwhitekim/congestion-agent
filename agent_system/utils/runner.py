"""
세그먼트 분석 루프. main.py(CLI)와 web/backend/analyzer.py 양쪽이 공유한다.
LLM(두뇌 역할) + 도구(손발 역할) 루프는 ClaudeAgent에 있고,
여기서는 메타데이터 조회·세그먼트 분할·레코드 조립을 담당한다.
"""

import json
import uuid
from pathlib import Path
from typing import Callable

from utils.custom_logger import GetLogger
from utils.utils import _split_timeline

logger = GetLogger("main", None)  # 호출부에서 이미 등록된 인스턴스를 재사용


def run_segments(
    agent,
    video_capture,
    interval_sec: float,
    on_record: Callable[[dict], None] | None = None,
) -> tuple[list[dict], dict]:
    """
    video_capture에서 메타데이터를 읽고 세그먼트를 분할한 뒤,
    ClaudeAgent(판단 본체)를 순회 실행해 (레코드 리스트, video_info)를 반환한다.
    on_record: 레코드 완성 직후 호출할 콜백 (터미널 출력 등 표시 계층용).
    """
    video_info = video_capture.video_metadata
    segments = _split_timeline(video_info["duration_sec"], interval_sec)

    results = []
    total = len(segments)

    for index, segment in enumerate(segments, start=1):
        start_sec = segment["start_sec"]
        end_sec = segment["end_sec"]
        logger.info("Segment %d/%d: %ss~%ss", index, total, start_sec, end_sec)

        try:
            # 도구 호출 여부는 LLM(두뇌 역할)이 결정한다.
            content = video_capture.build_vision_content(start_sec, end_sec)
            result = agent.run(content)
            result["frame_timestamp"] = start_sec  # 어느 프레임인지 — 시스템이 추가
            record = {"segment_index": index, "segment": segment, "result": result}
            logger.info("Segment %d result: %s", index, json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            logger.exception("Segment %d analysis failed", index)
            record = {"segment_index": index, "segment": segment, "error": str(exc)}

        results.append(record)
        if on_record:
            on_record(record)

    return results, video_info


def save_result(
    results: list[dict],
    video_info: dict,
    video_path: str | Path,
    domain: str,
    model: str,
    interval_sec: float,
    results_dir: Path,
) -> Path:
    """분석 결과를 JSON으로 저장하고 저장 경로를 반환한다."""
    output = {
        "video": str(video_path),
        "domain": domain,
        "model": model,
        "interval_sec": interval_sec,
        "video_info": video_info,
        "segments": results,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    result_path = results_dir / f"{uuid.uuid4().hex[:12]}.json"
    result_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %s", result_path)
    return result_path
