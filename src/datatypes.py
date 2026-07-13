from dataclasses import dataclass, field


@dataclass
class PerceptionResult:
    """한 세그먼트의 객관적 사실. 이미지/픽셀 필드 없음."""
    timestamp: float            # 세그먼트 시작 시각(초)
    total: int                  # 총 인원
    density: float              # Line Density 값
    avg_speed: float            # track 평균 이동 속도 (px/s)
    zone_counts: dict[str, int] # 구역별 인원
    zone_density: dict[str, float]  # 구역별 정규화 밀도 (근사치, perception/zone_metrics.py 참고)
    concentration: float        # 구역 간 분포 집중도 (Herfindahl-Hirschman 지수)
    tracks: list[dict]          # raw: track_id, center, bbox (연구용 보존)
    cv_elapsed_sec: float        # 이 세그먼트 구간 동안 detect+track에 소요된 실제 시간 (초)


@dataclass
class AggregatedFacts:
    """trigger/agent에 전달되는 집계 사실. 변화량 포함."""
    current: PerceptionResult
    density_delta_ratio: float  # current.density / 직전 이동평균 (1.0 = 변화 없음)
    speed_trend: float          # 양수 = 가속, 음수 = 감속 (선형회귀 기울기)
    density_slope: float        # 양수 = 밀도 증가 추세, 음수 = 감소 추세 (선형회귀 기울기)
    level: str                  # "low" | "medium" | "high"
