"""
LLM 프로바이더 레지스트리.

config.AGENT_PROVIDER 값("anthropic" | "gemini")에 따라 provider를 고른다.
provider 클래스는 별도 인터페이스를 상속하지 않는다 — init_state/send/
extract_tool_calls/extract_text/append_tool_results 5개 메서드만 구현하면
agent/loop.py의 tool_use 루프가 그대로 돌린다(duck typing).

새 프로바이더를 추가하려면 이 패키지에 파일을 추가해 위 5개 메서드를 구현한
클래스를 만들고 아래 _PROVIDERS에 한 줄만 등록하면 된다. loop.py는 건드릴
필요 없다.
"""

import config
from .claude import ClaudeProvider
from .gemini import GeminiProvider

_PROVIDERS = {
    "anthropic": ClaudeProvider,
    "gemini": GeminiProvider,
}


def get_provider():
    provider_cls = _PROVIDERS.get(config.AGENT_PROVIDER)
    if provider_cls is None:
        raise ValueError(
            f"Unknown AGENT_PROVIDER: {config.AGENT_PROVIDER!r} "
            f"(choices: {sorted(_PROVIDERS)})"
        )
    return provider_cls()
