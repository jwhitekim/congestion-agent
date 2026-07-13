"""
표준 tool_use / end_turn 루프.

LLM은 판단(assessment, reasoning, action)만 생산한다.
숫자 사실(total_people, density 등)은 LLM 출력 스키마에 없으며
코드가 facts에서 직접 주입한다.
"""

import json
import time

import config
from datatypes import AggregatedFacts
from . import prompt, schema
from .providers import get_provider
from .tools import TOOLS, execute_tool

_provider = get_provider()


def _send_with_retry(provider, system_prompt: str, state, tools: list[dict], log=None):
    """
    provider.send()를 실행하고, provider.is_retryable()이 참인 예외에 한해
    지수 백오프로 재시도한다. LLM의 판단 자체를 재시도하는 것이 아니라
    API 왕복이 네트워크/rate limit/서버 오류로 실패했을 때만 개입한다 —
    reflection/self-correction과는 무관하다.
    """
    delay = config.AGENT_RETRY_BACKOFF_SEC
    attempt = 0
    while True:
        try:
            return provider.send(system_prompt, state, tools)
        except Exception as exc:
            if attempt >= config.AGENT_MAX_RETRIES or not provider.is_retryable(exc):
                raise
            attempt += 1
            if log is not None:
                log.warning(
                    f"API 호출 실패 ({type(exc).__name__}: {exc}) — "
                    f"재시도 {attempt}/{config.AGENT_MAX_RETRIES}, {delay:.1f}초 후"
                )
            time.sleep(delay)
            delay *= 2


def _run_tool_loop(
    provider,
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    facts: AggregatedFacts,
    log=None,
) -> tuple[str, list[dict], list[dict], list[dict]]:
    """
    tool_use 루프를 끝까지 실행하고 최종 텍스트를 반환한다.
    provider는 init_state/send/extract_tool_calls/extract_text/append_tool_results/
    extract_usage/is_retryable 7개 메서드만 구현하면 된다(duck typing) — agent/providers/의
    구체 클래스가 이를 만족한다.

    반환: (final_text, tool_calls_log, tool_raw, api_call_log)
      - tool_calls_log: [{"name": ..., "input": ...}, ...]
      - tool_raw: 도구 호출 결과 원본 리스트 (연구용, 절대 버리지 마라)
      - api_call_log: API 왕복별 [{"elapsed_sec", "input_tokens", "output_tokens",
        "stop_reason"}, ...] (연구용, 병목 진단용)
    """
    state = provider.init_state(user_message)
    tool_calls_log: list[dict] = []
    tool_raw: list[dict] = []
    api_call_log: list[dict] = []

    while True:
        call_start = time.perf_counter()
        response = _send_with_retry(provider, system_prompt, state, tools, log=log)
        call_elapsed = time.perf_counter() - call_start

        usage = provider.extract_usage(response)
        api_call_log.append(
            {
                "elapsed_sec": round(call_elapsed, 3),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "stop_reason": usage["stop_reason"],
            }
        )

        calls = provider.extract_tool_calls(response)

        if not calls:
            return provider.extract_text(response), tool_calls_log, tool_raw, api_call_log

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
        f"- 밀도 추세(density_slope): {facts.density_slope:+.4f}\n"
        f"- 혼잡 수준: {facts.level}\n"
    )


def _has_duplicate_tool_calls(tool_calls_log: list[dict]) -> bool:
    """같은 도구를 동일한 입력값(zone/metric 등)으로 두 번 이상 호출했는지 확인."""
    seen = set()
    for call in tool_calls_log:
        key = (call["name"], tuple(sorted(call["input"].items())))
        if key in seen:
            return True
        seen.add(key)
    return False


def run(facts: AggregatedFacts, trigger_name: str, log=None) -> dict:
    """
    트리거 발생 시 에이전트 루프를 실행한다.

    log: main.py의 GetLogger 인스턴스(선택). API 재시도 발생 시 log.warning으로
    기록한다 — 없으면 재시도는 조용히 진행된다(로깅만 생략, 재시도 자체는 동작).

    반환 dict:
      - LLM 판단 필드 (schema.py 참고)
      - total_people, density: 코드가 facts에서 주입 (LLM 생산 아님)
      - tool_called: bool
      - tool_raw: list[dict]  (연구용 raw 보존, 절대 버리지 마라)
      - api_call_breakdown: list[dict]  (연구용, API 왕복별 시간/토큰/stop_reason)
      - duplicate_tool_calls: bool  (같은 (zone, metric) 등으로 중복 호출했는지)
    """
    user_message = f"트리거 발생: {trigger_name}\n\n{_facts_to_text(facts)}\n위 사실을 바탕으로 상황을 판정하십시오."

    text, tool_calls_log, tool_raw, api_call_log = _run_tool_loop(
        _provider,
        system_prompt=prompt.SYSTEM_PROMPT,
        user_message=user_message,
        tools=TOOLS,
        facts=facts,
        log=log,
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
    validated["api_call_breakdown"] = api_call_log  # 연구용 raw, 절대 버리지 마라
    validated["duplicate_tool_calls"] = _has_duplicate_tool_calls(tool_calls_log)
    return validated
