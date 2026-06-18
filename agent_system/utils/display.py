# =============================================================================
# utils/display.py  —  콘솔 출력 유틸리티
# =============================================================================

LEVEL_ICON = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def print_result(result: dict) -> None:
    level = result.get("congestion_level", "?")
    print(f"  혼잡도  : {LEVEL_ICON.get(level, '⚪')} {level.upper()}")
    print(f"  인원수  : {result.get('people_count', '?')}명")
    print(f"  조치    : {result.get('action', '?')}")
    print(f"  근거    : {result.get('reasoning', '')}")
