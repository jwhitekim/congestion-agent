"""
파이프라인 오케스트레이션.

설계 원칙:
  perception → trigger → (트리거 시에만) agent

에이전트가 매 세그먼트가 아닌 트리거 시에만 깨는지가
코드 흐름에서 명확히 보여야 한다.
"""

import json
import sys
from pathlib import Path

from io_utils.sampler import get_video_fps, iter_frames
from io_utils.reporter import report_segment
from perception.pipeline import PerceptionPipeline
from trigger.history import SegmentHistory
from trigger import rules
from agent import loop as agent_loop

RESULTS_FILE = Path("results.json")


def main(video_path: str) -> None:
    fps = get_video_fps(video_path)
    pipeline = PerceptionPipeline(fps=fps)
    history = SegmentHistory()
    results = []

    for timestamp, frame in iter_frames(video_path):

        # ── 1단계: Perception (항상 실행) ──────────────────────────────
        perception_result = pipeline.feed(timestamp, frame)
        if perception_result is None:
            continue  # 아직 세그먼트 인터벌 미달

        # ── 2단계: Trigger (항상 실행) ─────────────────────────────────
        trigger_name, trigger_reason, agg_facts = rules.evaluate(perception_result, history)

        # ── 3단계: Agent (트리거 시에만 소환) ──────────────────────────
        agent_output = None
        if trigger_name is not None:
            agent_output = agent_loop.run(agg_facts, trigger_name)
        # trigger_name이 None이면 에이전트는 호출되지 않는다.
        # 이 분기가 설계의 핵심: 에이전트는 상시 감시자가 아니다.

        # ── 터미널 출력 (사람용) ────────────────────────────────────────
        report_segment(perception_result, trigger_name, trigger_reason, agent_output)

        # ── results.json 누적 (분석용, tool_raw 포함 전체 보존) ─────────
        entry = {
            "timestamp": perception_result.timestamp,
            "perception": {
                "total": perception_result.total,
                "density": perception_result.density,
                "avg_speed": perception_result.avg_speed,
                "zone_counts": perception_result.zone_counts,
                "tracks": perception_result.tracks,
            },
            "trigger": trigger_name,
            "trigger_reason": trigger_reason,
            "aggregated": {
                "density_delta_ratio": agg_facts.density_delta_ratio,
                "speed_trend": agg_facts.speed_trend,
                "level": agg_facts.level,
            },
            "agent": agent_output,  # None이면 그대로 null로 저장
        }
        results.append(entry)

    RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {RESULTS_FILE} ({len(results)}개 세그먼트)")


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "samples/supermarket.mp4"
    main(video)
