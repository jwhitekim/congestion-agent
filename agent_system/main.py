# =============================================================================
# main.py  —  진입점
#
#   [도메인 선택]  domains.load(args.domain)
#                       ↓  {"system_prompt": ..., "tools": [...]}
#   [두뇌 생성]   ClaudeAgent(system_prompt=..., tools=..., model=...)
#                       ↓  도메인이 외부에서 주입된 두뇌
#   [프레임 분석]  agent.run(frame)  →  판단 결과 dict
# =============================================================================

import argparse
import json
import sys
from pathlib import Path

import domains
from agent import ClaudeAgent, DEFAULT_MODEL, MODEL_ALIASES
from utils.display import print_result
from utils.video import sample_frames
from utils.custom_logger import GetLogger
from dotenv import load_dotenv

logger = GetLogger("main", "logs/main.log")


def main():
    parser = argparse.ArgumentParser(description="에이전트 기반 영상 분석 MVP")
    parser.add_argument("--video", help="분석할 동영상 파일 경로")
    parser.add_argument("--interval", type=int, default=5, help="샘플링 간격(초), 기본: 5")
    parser.add_argument(
        "--domain",
        default="congestion",
        help=f"분석 도메인. 사용 가능: {list(domains.REGISTRY)}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(MODEL_ALIASES.keys()),
        help=f"사용할 모델: opus / sonnet / haiku (기본: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()
    load_dotenv()

    if not args.video:
        parser.error("--video 인자가 필요합니다.")
    if not Path(args.video).exists():
        logger.error(f"파일 없음: {args.video}")
        sys.exit(1)

    # ── [도메인 선택] ─────────────────────────────────────────────────────────
    try:
        domain_config = domains.load(args.domain)
    except ValueError as e:
        logger.error(f"도메인 오류: {e}")
        sys.exit(1)

    # ── [두뇌 생성 — 도메인을 외부에서 주입] ─────────────────────────────────
    try:
        agent = ClaudeAgent(
            system_prompt=domain_config["system_prompt"],
            tools=domain_config["tools"],
            model=MODEL_ALIASES[args.model],
        )
    except RuntimeError as e:
        logger.error(f"초기화 실패: {e}")
        sys.exit(1)

    results = []
    logger.info(f"도메인: {args.domain} | 모델: {args.model} ({MODEL_ALIASES[args.model]}) | 동영상: {args.video} | 간격: {args.interval}초")

    # ── [프레임별 분석] ───────────────────────────────────────────────────────
    for frame, timestamp in sample_frames(args.video, args.interval):
        logger.info(f"[{timestamp:6.1f}초] 분석 중...")
        try:
            result = agent.run(frame)
            result["timestamp"] = timestamp
            results.append(result)
            print_result(result)
        except Exception as e:
            logger.error(f"프레임 분석 오류 ({timestamp:.1f}초): {e}")
            results.append({"timestamp": timestamp, "error": str(e)})

    # ── [결과 저장] ───────────────────────────────────────────────────────────
    output = "results.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"완료: {len(results)}프레임 → {output}")


if __name__ == "__main__":
    main()
