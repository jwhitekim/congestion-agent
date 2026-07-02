"""
표준 tool_use / end_turn 루프.

LLM은 판단(assessment, reasoning, action)만 생산한다.
숫자 사실(total_people, density 등)은 LLM 출력 스키마에 없으며
코드가 facts에서 직접 주입한다.
"""

import json
import anthropic

from agent import config
from agent.types import AggregatedFacts
from .. import prompt, schema
from ..tools import TOOLS, execute_tool

_client = anthropic.Anthropic()


def _facts_to_text(facts: AggregatedFacts) -> str:
    c = facts.current
    zones = "  ".join(f"{z}={n}명" for z, n in c.zone_counts.items())
    return (
        "[집계 사실]\n"
        f"- 총 인원: {c.total}명\n"
        f"- 밀도(density): {c.density:.1f}\n"
        f"- 평균 속도: {c.avg_speed:.2f} px/s\n"
        f"- 구역별 인원: {zones}\n"
        f"- 밀도 변화율: {facts.density_delta_ratio:.2f}x (직전 평균 대비)\n"
        f"- 속도 추세: {facts.speed_trend:+.4f}\n"
        f"- 혼잡 수준: {facts.level}\n"
    )


def run(facts: AggregatedFacts, trigger_name: str) -> dict:
    """
    트리거 발생 시 에이전트 루프를 실행한다.
    반환 dict:
      - LLM 판단 필드 (schema.py 참고)
      - total_people, density: 코드가 facts에서 주입 (LLM 생산 아님)
      - tool_called: bool
      - tool_raw: list[dict]  (연구용 raw 보존, 절대 버리지 마라)
    """
    user_message = f"트리거 발생: {trigger_name}\n\n{_facts_to_text(facts)}\n위 사실을 바탕으로 상황을 판정하십시오."
    messages = [{"role": "user", "content": user_message}]

    tool_calls_log: list[dict] = []
    tool_raw: list[dict] = []

    while True:
        response = _client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=prompt.SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                parsed = json.loads(text[start:end])
                validated = schema.validate(parsed)
            except (json.JSONDecodeError, ValueError) as e:
                validated = {
                    "assessment": "caution",
                    "distribution_summary": "파싱 실패",
                    "congestion_level": facts.level,
                    "local_hotspots": [],
                    "reasoning": f"LLM 응답 파싱 오류: {e}",
                    "action": "monitor",
                }

            # 숫자 사실은 코드가 주입 — LLM이 생산한 값이 아님
            validated["total_people"] = facts.current.total
            validated["density"] = facts.current.density
            validated["trigger"] = trigger_name
            validated["tool_called"] = bool(tool_calls_log)
            validated["tool_raw"] = tool_raw  # 연구용 raw, 절대 버리지 마라
            return validated

        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_calls_log.append({"name": block.name, "input": block.input})

                result = execute_tool(block.name, facts, **block.input)

                tool_raw.append(result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            messages.append({"role": "user", "content": tool_results})

        else:
            # 비정상 stop_reason
            return _fallback(facts, trigger_name, tool_calls_log, tool_raw)


def _fallback(facts: AggregatedFacts, trigger_name: str, tool_calls_log: list, tool_raw: list) -> dict:
    return {
        "assessment": "caution",
        "distribution_summary": "루프 비정상 종료",
        "congestion_level": facts.level,
        "local_hotspots": [],
        "reasoning": "에이전트 루프가 비정상 종료됨.",
        "action": "monitor",
        "total_people": facts.current.total,
        "density": facts.current.density,
        "trigger": trigger_name,
        "tool_called": bool(tool_calls_log),
        "tool_raw": tool_raw,
    }
