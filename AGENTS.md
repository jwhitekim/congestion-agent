# AGENTS.md — 아키텍처 원칙

이 문서는 `congestion-agent`를 수정하거나 확장할 때 지켜야 할 설계 원칙을 정리한다.
코드를 고치기 전에 먼저 읽을 것. 여기 적힌 경계를 어기면 시스템 전체의 전제가 무너진다.

## 0. 용어 정의

이 리포에서 다음 세 단어는 서로 바꿔 쓸 수 없다.

- **agent system** — perception → trigger → agent로 이어지는 전체 파이프라인. `main.py`가 오케스트레이션하는 것 전부를 가리킨다.
- **LLM** — `agent/loop.py`가 호출하는 추론 컴포넌트. 사실을 받아 판단(assessment/reasoning/action)만 생산한다.
- **tool** — `agent/tools/`에 등록된 측정 컴포넌트. `AggregatedFacts`에서 사실을 읽어 dict로 반환한다. 판단하지 않는다.

"brain"(LLM을 가리킴), "limbs"(perception/tool을 가리킴) 같은 표현은 설명 중 괄호 한정어로만 쓴다.
예: `LLM(brain 역할)`. 코드 주석을 포함해 이 단어들을 독립 명사로 쓰지 않는다 — "the brain decides", "limbs collect data" 같은 문장은 금지.

## 1. 패키지 위계 — perception/trigger/agent는 형제다

```
src/
├── perception/    LLM 없음, 상시 실행, 도메인 무관해야 함
├── trigger/       rule 기반 게이팅. agent를 부를지 결정
├── agent/         LLM 판단. trigger가 부를 때만 동작 (loop, prompt, schema, tools/)
├── io_utils/       영상 입출력 + 터미널 리포팅
├── config.py       공용 설정 (세 레이어가 모두 참조)
├── datatypes.py     공용 dataclass (PerceptionResult, AggregatedFacts)
└── main.py          오케스트레이션 — 위 레이어를 조립하는 유일한 지점
```

`agent`는 이 중 하나일 뿐이지 상위 개념이 아니다. **perception이나 trigger를 `agent/` 밑에 다시 넣지 말 것** — perception은 LLM을 전혀 모르는 독립 레이어이므로 `agent.perception` 같은 import 경로가 생기면 위계가 뒤집힌다.

`config.py`, `datatypes.py`가 최상위에 있는 이유도 같다 — 세 레이어가 다 같이 참조하는 공용 모듈을 특정 레이어(agent) 소유로 두면 다른 레이어가 agent에 의존하는 꼴이 된다. 새 공용 모듈이 필요하면 특정 레이어 밑이 아니라 `src/` 최상위에 추가한다.

### 이름에 대한 주의

- `datatypes.py`(표준 라이브러리 `types`와 충돌 방지), `io_utils/`(표준 라이브러리 `io`와 충돌 방지)처럼 최상위 loose 모듈/패키지 이름은 **표준 라이브러리 이름과 겹치지 않아야 한다.** `PYTHONPATH=src`로 실행하는 구조라 `src/`가 `sys.path`에 직접 올라가므로, `types.py`나 `io.py`처럼 짓는 순간 표준 라이브러리보다 먼저 잡혀서 예측 불가능한 버그가 생긴다. 새 최상위 모듈을 추가할 때 이 이름 검증을 항상 먼저 할 것.

## 2. perception → trigger → agent 흐름

```
perception (항상 실행) → trigger (항상 실행) → agent (트리거 시에만 소환)
```

- **perception** (`perception/pipeline.py`): 모든 프레임을 tracker에 먹이지만, `SEGMENT_INTERVAL`마다 한 번만 `PerceptionResult`를 방출한다. 이미지/픽셀 필드를 포함하지 않는다.
- **trigger** (`trigger/rules.py`): 매 세그먼트마다 실행되며 `PerceptionResult` + `SegmentHistory`를 받아 트리거 여부를 rule로 판정한다. **순간값이 아니라 변화율·지속시간 기반**이어야 한다 (`density_delta_ratio`, `low_speed_streak_sec` 등). 새 트리거를 추가할 때도 이 기준을 지킬 것 — 임계값 하나만 보고 즉시 발동하는 rule은 추가하지 않는다. 시스템 전체 가치가 이 레이어의 게이팅 판단에 달려 있으므로, trigger 로직을 단순 스캐폴딩으로 취급할지 그 자체를 연구 대상으로 승격할지는 별도로 결정할 문제이며 현재는 미결정 상태다.
- **agent** (`agent/loop.py`): 트리거가 있을 때만 호출된다. `main.py`의 `if trigger_name is not None:` 분기가 이 설계의 핵심이며, 이 분기를 없애거나 매 세그먼트 호출로 바꾸는 변경은 금지한다. LLM API latency는 per-frame 실시간 요건과 구조적으로 양립하지 않는다 — agent는 실시간 감시자가 아니라 트리거로 소환되는 의사결정자다.

## 3. tools = facts, LLM = judgment

이 경계가 시스템 전체를 지탱한다. 위반하면 LLM이 도구를 우회해 직접 카운팅하는 문제(과거 시스템에서 실제로 발생: 가시 인원 ~15명인데 track 42개 보고)가 재발한다.

- LLM은 **텍스트/숫자만** 입력받는다. 이미지·픽셀은 절대 LLM에 전달하지 않는다 (`agent/loop.py`의 `_facts_to_text`가 유일한 입력 경로). VLM을 쓰지 않는 이유가 이것이다 — 텍스트 전용 입력은 우회 가능성을 구조적으로 차단하는 장치지, 단순한 비용 절감이 아니다.
- LLM 출력 스키마(`agent/schema.py`의 `REQUIRED_FIELDS`)에는 `total_people` 같은 숫자 카운트 필드가 없다. 이런 필드는 **코드가 `facts`에서 직접 주입**한다 (`loop.py`의 `validated["total_people"] = facts.current.total`). `schema.validate()`는 LLM이 몰래 숫자 필드를 생산해도 `_FORBIDDEN_NUMERIC`으로 걷어낸다 — 이 방어를 제거하지 말 것.
- `tool_raw`는 도구 호출 원본을 그대로 보존한다 (연구용). 요약하거나 버리지 않는다.
- 새 tool을 추가할 때: `run(facts, **kwargs) -> dict`는 반드시 사실만 반환해야 하고, 그 안에서 판단(assessment, action 등)을 생산하면 안 된다. 판단은 LLM의 몫이다.

## 4. registry + interface 패턴

새 도구는 기존 파일(`loop.py`, `agent/tools/__init__.py`)을 수정하지 않고 `agent/tools/`에 파일 하나만 추가하면 자동 인식되어야 한다.

```python
from . import register_tool

@register_tool(name="...", description="...", input_schema={...})
def my_tool(facts: AggregatedFacts, **kwargs) -> dict:
    ...
```

`agent/tools/__init__.py`는 `pkgutil.iter_modules`로 패키지 내 모든 모듈을 자동 import하므로, 새 파일을 추가하고 `@register_tool`만 붙이면 `loop.py`가 아무 것도 모른 채 그 도구를 LLM에 노출한다. `loop.py`가 개별 도구 이름을 import하거나 if/elif로 분기하는 코드를 추가하지 말 것 — 그 순간 이 패턴이 깨진다.

### action 레이어 (미구현 — TODO)

tool(read, LLM 루프 안에서 호출)과 action(write, 판단 이후 부수효과 실행)은 성격이 반대이며 같은 레이어에 두지 않는다.

|           | tool                      | action                                          |
| --------- | ------------------------- | ----------------------------------------------- |
| 목적      | 사실을 가져옴 (read)      | 세상을 바꿈 (write)                             |
| 호출 시점 | LLM이 루프 중 호출        | 판단 _후_ dispatcher가 실행                     |
| 반환      | 사실(dict)                | 실행 결과 (부수효과)                            |
| 위치      | `agent/tools/` (agent 안) | `action/` (agent 밖, `src/` 최상위 형제 레이어) |

현재 `main.py`는 `agent_output`을 받아 출력·저장만 하고 실제로 실행(dispatch)하지 않는다. `action/` 디렉토리는 아직 없다. 나중에 alert/로깅 등 실제 부수효과가 필요해지면 `action/base.py`(Action ABC), `action/registry.py`(`@register` + `ACTIONS`), `action/dispatcher.py`(`assessment["action"]` 필드를 보고 해당 Action 실행)로 구성하고, `perception`/`trigger`/`agent`와 동등한 `src/` 최상위 형제로 둔다. `agent/` 안에 두지 말 것 — 결정(judgment)과 실행(effect)도 사실↔판단 분리의 연장이다.

## 5. 패키징에 대한 현재 방침

지금은 `pyproject.toml`이 없다. 폴더 구조가 확정되지 않은 상태에서 패키징(entry point, 설치 방식)까지 같이 고민하면 결정할 게 늘어나기만 하므로 의도적으로 미룬 상태다. 실행은 `PYTHONPATH=src python src/main.py <video>` 방식으로 한다. 구조가 안정되면 `pyproject.toml`을 다시 추가하고, 그때 `datatypes.py`/`io_utils/` 같은 이름 충돌 회피가 여전히 유효한지 다시 점검한다.

## 6. 하지 말 것

- perception이 매 프레임 LLM을 호출하게 만들지 말 것 (latency, 비용, 그리고 "모든 프레임이 LLM을 거치는" 구조적 오류의 재발).
- LLM에게 이미지를 주지 말 것.
- tool의 `run()` 안에서 판단 필드를 생산하지 말 것.
- `schema.py`의 forbidden-field 방어를 우회하거나 제거하지 말 것.
- 트리거를 순간값 임계치 하나로 단순화하지 말 것 — 변화율/지속시간 기반을 유지할 것.
- action을 tool과 같은 디렉토리·같은 인터페이스로 섞지 말 것.
- perception/trigger를 `agent/` 밑으로 다시 넣지 말 것 (1절 위계 참고).
- 최상위 loose 모듈에 표준 라이브러리와 겹치는 이름을 쓰지 말 것.
