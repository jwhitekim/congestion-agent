# =============================================================================
# agent/agent.py  —  두뇌: ClaudeAgent
#
# 이 클래스는 도메인을 전혀 모른다.
# "도구를 호출하고 → 결과를 수집하고 → 최종 판단을 받는다"는 흐름만 구현한다.
#
# 도메인(혼잡도, 행동인식, 화재감지 …)은 생성자 인자로 외부에서 주입된다.
# 도메인을 바꾸고 싶다면 이 파일은 건드리지 않아도 된다.
# =============================================================================

import base64
import json
import os
from typing import List

import anthropic
import cv2
import numpy as np

# 두뇌는 BaseTool 인터페이스만 안다. 구체적인 도구 클래스는 모른다.
from tools.base import BaseTool


# 짧은 별칭 → 실제 모델 ID
MODEL_ALIASES = {
    "opus":   "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5-20251001",
}
DEFAULT_MODEL = "opus"


class ClaudeAgent:
    """
    도메인 중립적인 에이전트 두뇌.

    ┌─────────────────────────────────────────────────────────┐
    │  두뇌의 단일 책임:                                        │
    │  1. 이미지를 Claude에 전달                                │
    │  2. Claude의 도구 호출 요청 → 실제 도구로 연결 (루프)      │
    │  3. Claude의 최종 JSON 판단을 파싱해 반환                 │
    │                                                         │
    │  두뇌가 모르는 것: 도메인, 도구의 구체적 동작, 출력 형식    │
    └─────────────────────────────────────────────────────────┘

    도메인 주입:
        ClaudeAgent(system_prompt="혼잡도 판단 지시문", tools=[CountPeopleTool()])
        → 동일한 두뇌를 어떤 도메인에도 재사용 가능.
    """

    def __init__(self, system_prompt: str, tools: List[BaseTool], model: str = DEFAULT_MODEL):
        # ── 두뇌 초기화 ────────────────────────────────────────────────────────
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
                "  Windows PowerShell : $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
                "  Mac/Linux          : export ANTHROPIC_API_KEY=sk-ant-..."
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

        # ── 손발 등록 ──────────────────────────────────────────────────────────
        # 두뇌는 도구 이름으로만 도구를 찾는다. 구현 내용은 모른다.
        self.tools: List[BaseTool] = tools
        self._tool_map: dict[str, BaseTool] = {t.schema["name"]: t for t in tools}

    # ─────────────────────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────────────────────────────────────

    def _to_base64(self, frame: np.ndarray) -> str:
        """OpenCV BGR 프레임 → base64 JPEG 문자열."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf).decode("utf-8")

    def _dispatch(self, tool_name: str, tool_input: dict) -> str:
        """
        Claude가 요청한 도구를 찾아 실행하고 JSON 문자열을 반환한다.

        두뇌는 도구가 무엇을 하는지 모른다.
        이름으로 찾아 run()을 호출할 뿐이다.
        """
        tool = self._tool_map.get(tool_name)
        if tool is None:
            return json.dumps({"error": f"등록되지 않은 도구: {tool_name}"})
        try:
            result = tool.run(tool_input)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": f"도구 실행 오류: {e}"})

    def _parse_json(self, text: str) -> dict:
        """Claude 텍스트 응답에서 JSON 객체를 추출·파싱한다."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"JSON 파싱 실패:\n{text}")

    # ─────────────────────────────────────────────────────────────────────────
    # 핵심 메서드 — 두뇌의 전체 실행 흐름
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, image: np.ndarray) -> dict:
        """
        이미지 한 장을 받아 최종 판단 JSON을 반환한다.

        흐름:
          [1] 손발 도구에 현재 프레임 주입 (prepare)
          [2] Claude에 이미지 + 도구 스키마 전달
          [3] tool_use 루프: 도구 호출 → 결과 반환 → 재호출 …
          [4] end_turn: 최종 JSON 파싱 후 반환
        """
        # ── [1] 손발에 현재 컨텍스트 주입 ────────────────────────────────────
        context = {"frame": image}
        for tool in self.tools:
            tool.prepare(context)

        # ── [2] 초기 메시지 구성: 이미지 + 분석 요청 ─────────────────────────
        tool_schemas = [t.schema for t in self.tools]
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": self._to_base64(image),
                        },
                    },
                    {
                        "type": "text",
                        "text": "이 장면을 분석하라. 필요한 도구를 먼저 호출한 뒤 최종 판단을 JSON으로 출력하라.",
                    },
                ],
            }
        ]

        # ── [3] tool use 루프 ────────────────────────────────────────────────
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                tools=tool_schemas,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"    → 도구 호출: {block.name}")
                        result_str = self._dispatch(block.name, block.input)
                        print(f"    ← 결과    : {json.loads(result_str)}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })

                messages.append({"role": "user", "content": tool_results})

            # ── [4] 최종 판단 ─────────────────────────────────────────────────
            elif response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text") and block.text.strip():
                        return self._parse_json(block.text)
                raise ValueError("Claude 응답에 텍스트 블록이 없습니다.")

            else:
                raise ValueError(f"예상치 못한 stop_reason: {response.stop_reason}")
