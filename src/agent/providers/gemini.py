"""
Google Gemini 프로바이더 (Interactions API, google-genai SDK).
tool_use 루프 골격은 providers/__init__.py의 run_tool_loop()가 담당한다.
이 클래스는 init_state/send/extract_tool_calls/extract_text/append_tool_results/extract_usage
6개 메서드만 맞추면 되고 별도 인터페이스는 상속하지 않는다(duck typing).

tool 스키마는 agent/tools/에서 Anthropic 형식(input_schema)으로 등록되므로,
Gemini가 요구하는 {"type": "function", ..., "parameters": ...} 형식으로
이 파일 안에서만 변환한다. agent/tools/ 쪽은 건드리지 않는다.
"""

import json

from google import genai

import config


def _to_gemini_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }
        for t in tools
    ]


class GeminiProvider:
    def __init__(self):
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    def init_state(self, user_message: str) -> dict:
        return {"previous_interaction_id": None, "input": user_message}

    def send(self, system_prompt: str, state: dict, tools: list[dict]):
        kwargs = {
            "model": config.GEMINI_MODEL,
            "tools": _to_gemini_tools(tools),
            "input": state["input"],
        }
        if state["previous_interaction_id"] is None:
            kwargs["system_instruction"] = system_prompt
        else:
            kwargs["previous_interaction_id"] = state["previous_interaction_id"]
        return self._client.interactions.create(**kwargs)

    def extract_tool_calls(self, response) -> list[dict]:
        return [
            {"id": s.id, "name": s.name, "args": s.arguments}
            for s in (response.steps or [])
            if s.type == "function_call"
        ]

    def extract_text(self, response) -> str:
        return response.output_text or ""

    def extract_usage(self, response) -> dict:
        usage = response.usage
        return {
            "input_tokens": usage.total_input_tokens if usage else None,
            "output_tokens": usage.total_output_tokens if usage else None,
            "stop_reason": response.status,
        }

    def append_tool_results(self, state: dict, response, calls: list[dict], results: list[dict]) -> dict:
        function_results = [
            {
                "type": "function_result",
                "name": call["name"],
                "call_id": call["id"],
                "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            }
            for call, result in zip(calls, results)
        ]
        return {"previous_interaction_id": response.id, "input": function_results}
