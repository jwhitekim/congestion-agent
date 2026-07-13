"""
세션 폴더(outputs/<timestamp>/) 및 결과 파일(session.json, results.jsonl) 관리.
main.py는 이 클래스를 통해서만 세션 파일에 접근한다.
"""

import json
from datetime import datetime
from pathlib import Path

import config

OUTPUTS_DIR = Path("outputs")


def _config_snapshot() -> dict:
    return {
        "SURGE_RATIO": config.SURGE_RATIO,
        "SPEED_MIN": config.SPEED_MIN,
        "STAG_SEC": config.STAG_SEC,
        "ZONE_MAX": config.ZONE_MAX,
        "SEGMENT_INTERVAL": config.SEGMENT_INTERVAL,
    }


class SessionFileManager:
    def __init__(self, video_path: str, outputs_dir: Path = OUTPUTS_DIR):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = outputs_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.session_dir / "session.json"
        self.results_file = self.session_dir / "results.jsonl"
        self.segment_count = 0

        self._session = {
            "session_id": self.session_id,
            "video_path": video_path,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "config_snapshot": _config_snapshot(),
        }
        self._write_session()
        self._results_fh = open(self.results_file, "a", encoding="utf-8")

    def _write_session(self) -> None:
        self.session_file.write_text(json.dumps(self._session, ensure_ascii=False, indent=2))

    def write_segment(self, perception_result, trigger_name, trigger_reason, agg_facts, agent_output) -> None:
        entry = {
            "timestamp": perception_result.timestamp,
            "perception": {
                "total": perception_result.total,
                "density": perception_result.density,
                "avg_speed": perception_result.avg_speed,
                "zone_counts": perception_result.zone_counts,
                "zone_density": perception_result.zone_density,
                "concentration": perception_result.concentration,
                "tracks": perception_result.tracks,
            },
            "trigger": trigger_name,
            "trigger_reason": trigger_reason,
            "aggregated": {
                "density_delta_ratio": agg_facts.density_delta_ratio,
                "speed_trend": agg_facts.speed_trend,
                "density_slope": agg_facts.density_slope,
                "level": agg_facts.level,
            },
            "agent": agent_output,  # None이면 그대로 null로 저장
        }
        self._results_fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._results_fh.flush()
        self.segment_count += 1

    def close(self) -> None:
        self._results_fh.close()
        self._session["ended_at"] = datetime.now().isoformat()
        self._session["segment_count"] = self.segment_count
        self._write_session()
