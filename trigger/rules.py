from typing import Optional
import config
from facts.types import PerceptionResult, AggregatedFacts
from .history import SegmentHistory


def _classify_level(density: float) -> str:
    if density < config.DENSITY_LOW:
        return "low"
    elif density < config.DENSITY_HIGH:
        return "medium"
    return "high"


def evaluate(
    current: PerceptionResult,
    history: SegmentHistory,
) -> tuple[Optional[str], Optional[str], AggregatedFacts]:
    """
    현재 PerceptionResult와 히스토리를 받아 트리거 여부를 판정한다.

    반환: (trigger_name, reason, AggregatedFacts)
    트리거 없으면 trigger_name=None, reason=None.

    순간값이 아닌 변화율·지속시간 기반 조건을 사용한다.
    이 레이어는 agent/ 를 import하지 않는다.
    """
    avg_density = history.avg_density()
    density_delta_ratio = (
        current.density / avg_density if avg_density > 0 else 1.0
    )
    trend = history.speed_trend_with(current.avg_speed)
    level = _classify_level(current.density)

    facts = AggregatedFacts(
        current=current,
        density_delta_ratio=density_delta_ratio,
        speed_trend=trend,
        level=level,
    )

    # 현재값을 히스토리에 추가 (delta 계산 이후에 추가해야 직전 평균이 기준이 됨)
    history.add(current)

    # --- 트리거 조건: 순간값이 아니라 변화·지속 기반 ---

    # 1. Surge: density가 직전 이동평균의 SURGE_RATIO 배 초과
    if len(history) >= 2 and density_delta_ratio > config.SURGE_RATIO:
        reason = (
            f"density {current.density:.1f} > "
            f"avg {avg_density:.1f} × {config.SURGE_RATIO} "
            f"(ratio={density_delta_ratio:.2f})"
        )
        return "surge", reason, facts

    # 2. Stagnation: 속도가 SPEED_MIN 미만으로 STAG_SEC 초 이상 지속
    history_streak = history.low_speed_streak_sec(config.SPEED_MIN, config.SEGMENT_INTERVAL)
    # current가 이미 history에 추가됐으므로 streak에 포함됨
    if history_streak >= config.STAG_SEC:
        reason = (
            f"avg_speed {current.avg_speed:.2f} px/s < {config.SPEED_MIN} "
            f"for {history_streak:.0f}s"
        )
        return "stagnation", reason, facts

    # 3. Hotspot: 한 구역 인원이 ZONE_MAX 초과
    if current.zone_counts:
        hotspot_zone = max(current.zone_counts, key=current.zone_counts.get)
        hotspot_count = current.zone_counts[hotspot_zone]
        if hotspot_count > config.ZONE_MAX:
            reason = f"hotspot: {hotspot_zone}구역 {hotspot_count}명 > 임계 {config.ZONE_MAX}"
            return "hotspot", reason, facts

    return None, None, facts
