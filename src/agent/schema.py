"""
LLM 출력 스키마 검증.
total_people 등 숫자 카운트 필드는 스키마에 없다 — 코드가 주입한다.
"""

REQUIRED_FIELDS = {
    "assessment",
    "distribution_summary",
    "congestion_level",
    "local_hotspots",
    "reasoning",
    "action",
}

VALID_ASSESSMENT = {"normal", "caution", "anomaly"}
VALID_LEVEL = {"low", "medium", "high"}
VALID_ACTION = {"none", "monitor", "alert"}

# LLM이 몰래 숫자를 생산하면 걷어낸다
_FORBIDDEN_NUMERIC = {"total_people", "total", "count", "num_people", "people_count"}


def validate(data: dict) -> dict:
    """검증 + 금지 필드 제거. 실패 시 ValueError."""
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"Missing fields in LLM output: {missing}")

    if data["assessment"] not in VALID_ASSESSMENT:
        raise ValueError(f"Invalid assessment: {data['assessment']!r}")
    if data["congestion_level"] not in VALID_LEVEL:
        raise ValueError(f"Invalid congestion_level: {data['congestion_level']!r}")
    if data["action"] not in VALID_ACTION:
        raise ValueError(f"Invalid action: {data['action']!r}")

    # 금지 필드 제거 (LLM 우회 방어)
    for field in _FORBIDDEN_NUMERIC:
        data.pop(field, None)

    return data
