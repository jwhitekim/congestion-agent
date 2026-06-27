import json
import os
from pathlib import Path
from typing import List

import anthropic

from .base import BaseTool
from utils.custom_logger import GetLogger
from dotenv import load_dotenv

_LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
logger = GetLogger("agent", str(_LOGS_DIR / "agent.log"))


MODEL_ALIASES = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}
DEFAULT_MODEL = "sonnet"


class ClaudeAgent:
    """
    LLM + tool use 루프를 감싼 에이전트 시스템의 판단 본체. 도메인 중립.

    이 클래스는 특정 도메인을 모른다. system_prompt와 tools를 외부에서 주입받고,
    LLM(두뇌 역할)이 필요하다고 판단한 도구(손발 역할)만 실행한 뒤 최종 JSON을 반환한다.
    비디오, 이미지 등 입력 모달리티도 모른다. content 리스트를 받아 tool-use 루프만 돌린다.
    """

    def __init__(self, system_prompt: str, tools: List[BaseTool], model: str = MODEL_ALIASES[DEFAULT_MODEL]):
        load_dotenv()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is required.")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self._tool_map: dict[str, BaseTool] = {tool.schema["name"]: tool for tool in tools}

    def _dispatch(self, tool_name: str, tool_input: dict) -> tuple[str, dict | None]:
        """
        LLM(두뇌 역할)이 요청한 도구(손발 역할)를 이름으로 찾아 실행한다.
        (JSON 문자열, 파싱된 raw dict) 쌍을 반환한다. 도구 실패 시 raw는 None.
        """
        tool = self._tool_map.get(tool_name)
        if tool is None:
            err = json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
            return err, None

        try:
            result = tool.run(tool_input)
            return json.dumps(result, ensure_ascii=False), result
        except Exception as exc:
            logger.exception("Tool execution failed: %s", tool_name)
            err = json.dumps({"error": f"Tool failed: {exc}"}, ensure_ascii=False)
            return err, None

    def _build_tool_raw(self, raw: dict) -> dict:
        """
        도구(손발 역할)의 raw 출력에서 연구 비교용 핵심 사실만 추출한다.
        # 도구가 준 사실 vs LLM(두뇌 역할)의 분포 판단을 나중에 비교하기 위한 연구용 데이터.
        # 절대 버리지 말 것 — 이게 에이전트 시스템의 연구 칼날이다.
        zone_counts: 구역별 최종 인원 (list → dict 변환으로 가독성 확보)
        tracks: 각 사람의 마지막 위치 (frames_present는 제외해 용량 절감)
        """
        zone_counts = {
            item["zone"]: item["people_count"]
            for item in raw.get("zone_counts", [])
        }
        tracks = [
            {"track_id": p["track_id"], "center": p["center"], "bbox": p["bbox"]}
            for p in raw.get("people", [])
        ]
        return {"zone_counts": zone_counts, "tracks": tracks}

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Failed to parse JSON response:\n{text}")
        
    def run(self, content: list) -> dict:
        """
        호출자가 준비한 user content로 tool-use 루프를 수행한다.

        여기서 LLM(두뇌 역할)이 도구(손발 역할) 호출을 결정한다.
        LLM이 도구를 호출하면 그때 실행하고, 도구(손발 역할)가 준 사실을 다시 LLM에게 넘긴다.
        최종 판단은 LLM의 JSON 응답만 사용한다.
        반환 dict에 tool_called(bool)과 tool_raw(도구 원본 사실)가 시스템이 자동으로 추가된다.
        """
        messages = [{"role": "user", "content": content}]
        tool_schemas = [tool.schema for tool in self.tools]

        tool_called = False
        tool_raw: dict | None = None

        while True:
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=self.system_prompt,
                    tools=tool_schemas,
                    messages=messages,
                )
            except Exception as exc:
                raise RuntimeError(f"Claude API request failed: {exc}") from exc

            if response.stop_reason == "tool_use":
                tool_called = True
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    logger.info("Claude requested tool: %s", block.name)
                    result_str, raw_dict = self._dispatch(block.name, block.input)
                    # 도구(손발 역할)의 마지막 raw 출력을 보존한다 (연구용).
                    if raw_dict is not None:
                        tool_raw = self._build_tool_raw(raw_dict)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

                messages.append({"role": "user", "content": tool_results})
                continue

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text") and block.text.strip():
                        result = self._parse_json(block.text)
                        # LLM(두뇌 역할)의 판단 결과에 시스템 메타데이터를 추가한다.
                        result["tool_called"] = tool_called
                        result["tool_raw"] = tool_raw
                        return result
                raise ValueError("Claude returned no text block.")

            raise ValueError(f"Unexpected stop_reason: {response.stop_reason}")
