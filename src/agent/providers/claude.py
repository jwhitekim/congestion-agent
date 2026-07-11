"""
Anthropic Claude 프로바이더.
tool_use 루프 골격은 providers/__init__.py의 run_tool_loop()가 담당한다.
이 클래스는 다른 provider와 인터페이스를 상속하지 않는다 — init_state/send/
extract_tool_calls/extract_text/append_tool_results 5개 메서드만 맞추면
run_tool_loop()가 그대로 돌린다(duck typing).
"""

import json

import anthropic

import config


class ClaudeProvider:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=30.0)

    def init_state(self, user_message: str) -> list[dict]:
        return [{"role": "user", "content": user_message}]

    def send(self, system_prompt: str, state: list[dict], tools: list[dict]):
        return self._client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=state,
        )

    def extract_tool_calls(self, response) -> list[dict]:
        if response.stop_reason != "tool_use":
            return []
        return [
            {"id": block.id, "name": block.name, "args": block.input}
            for block in response.content
            if block.type == "tool_use"
        ]

    def extract_text(self, response) -> str:
        if response.stop_reason != "end_turn":
            return ""  # 비정상 stop_reason
        return "".join(block.text for block in response.content if hasattr(block, "text"))

    def append_tool_results(self, state: list[dict], response, calls: list[dict], results: list[dict]) -> list[dict]:
        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            }
            for call, result in zip(calls, results)
        ]
        return state + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results},
        ]
