import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

import domains
from agent import ClaudeAgent, DEFAULT_MODEL, MODEL_ALIASES
from utils.display import print_result
from utils.video import build_vision_content
from utils.custom_logger import GetLogger

logger = GetLogger("main", "logs/main.log")


def _load_video_info(video_path: Path) -> dict:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("opencv-python is required to read video metadata.") from exc

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            raise RuntimeError(f"Cannot read frame count: {video_path}")
        duration_sec = total_frames / fps if fps else None
        return {"fps": fps, "total_frames": total_frames, "duration_sec": duration_sec}
    finally:
        cap.release()


def _build_segments(duration_sec: float | None, interval_sec: float) -> list[dict]:
    if duration_sec is None:
        return [{"start_sec": 0.0, "end_sec": None}]

    segments = []
    start = 0.0
    while start < duration_sec:
        end = min(start + interval_sec, duration_sec)
        segments.append({"start_sec": round(start, 3), "end_sec": round(end, 3)})
        start = end
    return segments


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM tool-use based video analysis agent")
    parser.add_argument("--video", required=True, help="Path to the video file to analyze.")
    parser.add_argument("--interval", type=float, default=5.0, help="Segment interval in seconds. Default: 5.")
    parser.add_argument("--domain", default="congestion", help=f"Domain name. Available: {list(domains.REGISTRY)}")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODEL_ALIASES), help="Claude model alias.")
    args = parser.parse_args()

    load_dotenv()

    video_path = Path(args.video)
    if not video_path.exists():
        logger.error("Video file not found: %s", video_path)
        sys.exit(1)
    if args.interval <= 0:
        parser.error("--interval must be greater than 0.")

    try:
        # 도메인 설정 로드와 ClaudeAgent 생성은 분리한다. ClaudeAgent는 도메인을 모르고 prompt/tools만 주입받는다.
        domain_config = domains.load(args.domain)
        agent = ClaudeAgent(
            system_prompt=domain_config["system_prompt"],
            tools=domain_config["tools"],
            model=MODEL_ALIASES[args.model],
        )
        video_info = _load_video_info(video_path)
        segments = _build_segments(video_info["duration_sec"], args.interval)
    except Exception as exc:
        logger.error("Initialization failed: %s", exc)
        sys.exit(1)

    results = []
    for index, segment in enumerate(segments, start=1):
        start_sec = segment["start_sec"]
        end_sec = segment["end_sec"]
        logger.info("Analyzing segment %s/%s: %s~%s", index, len(segments), start_sec, end_sec)

        try:
            # 여기서 각 구간을 ClaudeAgent(판단 본체)에 넘긴다. 도구 호출 여부는 LLM(두뇌 역할)이 결정한다.
            content = build_vision_content(str(video_path), start_sec, end_sec)
            result = agent.run(content)
            record = {"segment_index": index, "segment": segment, "result": result}
            print_result(record)
        except Exception as exc:
            logger.exception("Segment analysis failed")
            record = {"segment_index": index, "segment": segment, "error": str(exc)}
            print_result(record)
        results.append(record)

    output = {
        "video": str(video_path),
        "domain": args.domain,
        "model": args.model,
        "interval_sec": args.interval,
        "video_info": video_info,
        "segments": results,
    }
    with open("results.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    logger.info("Saved results.json")


if __name__ == "__main__":
    main()
