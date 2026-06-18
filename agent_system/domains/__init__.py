# =============================================================================
# domains/__init__.py  —  도메인 레지스트리
#
# 새 도메인 추가 방법:
#   1. domains/ 아래에 새 모듈(예: action_recognition.py)을 만들고
#      get_domain() → {"system_prompt": ..., "tools": [...]} 구현
#   2. 아래 REGISTRY에 이름: 팩토리함수 형태로 등록
#   3. --domain 인자로 선택 가능해진다. 두뇌 코드는 한 줄도 안 바꿔도 됨.
# =============================================================================

from . import congestion

# 도메인 이름 → 설정 팩토리 함수 매핑
REGISTRY: dict = {
    "congestion": congestion.get_domain,
    # 향후 추가 예시:
    # "action": action_recognition.get_domain,
    # "fire":   fire_detection.get_domain,
}


def load(name: str) -> dict:
    """
    이름으로 도메인 설정을 불러온다.
    반환값: {"system_prompt": str, "tools": list[BaseTool]}
    """
    if name not in REGISTRY:
        available = ", ".join(REGISTRY.keys())
        raise ValueError(f"알 수 없는 도메인: '{name}'. 사용 가능: {available}")
    return REGISTRY[name]()
