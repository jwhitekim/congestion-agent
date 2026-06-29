"""
에이전트 도구 정의.
track_people: 특정 구역/지표의 사실을 텍스트/숫자로 반환. 이미지 없음.
"""

from facts.types import AggregatedFacts

TOOLS = [
    {
        "name": "track_people",
        "description": (
            "특정 구역 또는 지표의 정밀한 사실(인원·밀도·속도)을 반환합니다. "
            "텍스트/숫자 사실만 반환하며 이미지는 절대 반환하지 않습니다. "
            "판단에 사실이 부족할 때만 호출하십시오."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "조회할 구역. A/B/C 중 하나 또는 'all'(전체).",
                },
                "metric": {
                    "type": "string",
                    "enum": ["count", "density", "speed", "all"],
                    "description": "조회할 지표.",
                },
            },
            "required": ["zone", "metric"],
        },
    }
]


def track_people(facts: AggregatedFacts, zone: str, metric: str) -> dict:
    """
    AggregatedFacts에서 요청된 구역/지표 사실을 추출해 반환.
    출력은 텍스트/JSON 사실이며 이미지를 포함하지 않는다.
    """
    current = facts.current

    zone_data = (
        current.zone_counts
        if zone == "all"
        else {zone: current.zone_counts.get(zone, 0)}
    )

    result: dict = {"zone": zone, "metric": metric, "facts": {}}

    if metric in ("count", "all"):
        result["facts"]["zone_counts"] = zone_data
    if metric in ("density", "all"):
        result["facts"]["density"] = round(current.density, 2)
    if metric in ("speed", "all"):
        result["facts"]["avg_speed"] = round(current.avg_speed, 3)

    # 맥락 사실 항상 포함
    result["facts"]["density_delta_ratio"] = round(facts.density_delta_ratio, 3)
    result["facts"]["speed_trend"] = round(facts.speed_trend, 4)
    result["facts"]["level"] = facts.level

    return result
