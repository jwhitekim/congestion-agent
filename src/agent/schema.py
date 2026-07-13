"""
LLM 출력 스키마 검증.
total_people 등 숫자 카운트 필드와 congestion_level/local_hotspots는 스키마에
없다 — 전부 코드가 facts에서 직접 주입한다 (agent/loop.py 참고). congestion_level은
trigger/rules.py가 이미 계산한 사실이고, local_hotspots는 zone_counts를 ZONE_MAX와
비교하기만 하면 나오는 사실이라 LLM이 재생산할 이유가 없다 — LLM이 "본 것처럼"
숫자·등급을 만들어내는 우회 경로를 원천적으로 막는다.
"""

REQUIRED_FIELDS = {
    "assessment",
    "distribution_summary",
    "reasoning",
    "action",
}

VALID_ASSESSMENT = {"normal", "caution", "anomaly"}
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
    if data["action"] not in VALID_ACTION:
        raise ValueError(f"Invalid action: {data['action']!r}")

    # 금지 필드 제거 (LLM 우회 방어)
    for field in _FORBIDDEN_NUMERIC:
        data.pop(field, None)

    return data
