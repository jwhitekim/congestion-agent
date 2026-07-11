"""
표준 tool_use / end_turn 루프.

LLM은 판단(assessment, reasoning, action)만 생산한다.
숫자 사실(total_people, density 등)은 LLM 출력 스키마에 없으며
코드가 facts에서 직접 주입한다.
"""

import json

from datatypes import AggregatedFacts
from . import prompt, schema
from .providers import get_provider
from .tools import TOOLS, execute_tool

_provider = get_provider()


def _run_tool_loop(
    provider,
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    facts: AggregatedFacts,
) -> tuple[str, list[dict], list[dict]]:
    """
    tool_use 루프를 끝까지 실행하고 최종 텍스트를 반환한다.
    provider는 init_state/send/extract_tool_calls/extract_text/append_tool_results
    5개 메서드만 구현하면 된다(duck typing) — agent/providers/의 구체 클래스가 이를 만족한다.

    반환: (final_text, tool_calls_log, tool_raw)
      - tool_calls_log: [{"name": ..., "input": ...}, ...]
      - tool_raw: 도구 호출 결과 원본 리스트 (연구용, 절대 버리지 마라)
    """
    state = provider.init_state(user_message)
    tool_calls_log: list[dict] = []
    tool_raw: list[dict] = []

    while True:
        response = provider.send(system_prompt, state, tools)
        calls = provider.extract_tool_calls(response)

        if not calls:
            return provider.extract_text(response), tool_calls_log, tool_raw

        results = []
        for call in calls:
            tool_calls_log.append({"name": call["name"], "input": call["args"]})
            result = execute_tool(call["name"], facts, **call["args"])
            tool_raw.append(result)
            results.append(result)

        state = provider.append_tool_results(state, response, calls, results)


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

    text, tool_calls_log, tool_raw = _run_tool_loop(
        _provider,
        system_prompt=prompt.SYSTEM_PROMPT,
        user_message=user_message,
        tools=TOOLS,
        facts=facts,
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
