# congestion-agent — 아키텍처 원칙

이 문서는 congestion-agent를 수정/확장할 때 지켜야 할 설계 원칙이다.
코드를 고치기 전에 먼저 읽을 것. 여기 적힌 경계를 어기면 시스템 전체의 전제가 무너진다.
agent/, trigger/ 관련 세부 규칙은 `.claude/rules/`에 별도로 있고, 해당 경로 작업 시 자동 로드된다.

## 실행
- `make run` / `make run VIDEO=<path>` — PYTHONPATH=src python src/main.py 실행
- `make dash` / `make dash-build` — 대시보드

## 0. 용어 정의

- **agent system** — perception → trigger → agent 전체 파이프라인. `main.py`가 오케스트레이션.
- **LLM** — `agent/loop.py`가 호출하는 추론 컴포넌트. 사실을 받아 판단만 생산한다.
- **tool** — `agent/tools/`에 등록되어 사실을 조회만 하는 컴포넌트(현재 비어있음). 판단하지 않는다.

**"agent system"은 이 리포 내부 통칭이다.** NCISS 논문에서는 자율 에이전트가 아니라 **이벤트 트리거형 에이전틱 워크플로우(event-triggered agentic workflow)**로 분류한다(Anthropic 2024 taxonomy — 코드가 trigger·실행 경로를 통제, LLM은 트리거 시에만 국소 판단). "반자동"이라는 표현은 사람 개입을 뜻하는 것으로 오독될 수 있어 폐기했다(2026-07-15 확정). 이 분류는 현재 single-shot 구현에 한정된다 — `TOOL_ONLY`가 채워져 tool-use 루프가 복원되면 재검토 필요.

"brain"/"limbs" 같은 표현은 괄호 한정어로만 쓴다 (`LLM(brain 역할)`). 독립 명사로 쓰지 말 것.

## 1. 패키지 위계 — perception/trigger/agent는 형제다

```
src/
├── perception/    LLM 없음, 상시 실행, trigger/agent의 판단 정책을 모름
├── trigger/       rule 기반 게이팅. agent를 부를지 결정
├── agent/         LLM 판단. trigger가 부를 때만 동작 (loop, prompt, schema, providers/, tools/)
├── io_utils/       영상 입출력 + 터미널 리포팅 + 세션 파일 관리(session.json/results.jsonl)
├── config.py       공용 설정 (세 레이어가 모두 참조)
├── datatypes.py     공용 dataclass (PerceptionResult, AggregatedFacts) + 노출 레지스트리(3절)
└── main.py          오케스트레이션 — 위 레이어를 조립하는 유일한 지점
```

`agent`는 형제 중 하나일 뿐 상위 개념이 아니다. **perception/trigger를 `agent/` 밑에 다시 넣지 말 것.**
공용 모듈(`config.py`, `datatypes.py`)은 특정 레이어 소유로 두지 말고 `src/` 최상위에 둔다.

최상위 loose 모듈 이름은 표준 라이브러리와 겹치면 안 된다 (`datatypes.py`, `io_utils/`가 그 이유로 지어진 이름).

## 2. 파이프라인 흐름 (개요)

```
perception (항상 실행) → trigger (항상 실행) → agent (트리거 시에만 소환)
```

- perception: 이미지/픽셀 없이 관측값(`PerceptionResult`)만 방출
- trigger: rule 기반으로 agent 호출 여부 결정 — 세부 계약은 `.claude/rules/trigger.md` 참고
- agent: 트리거된 경우에만 호출, 실시간 감시자 아님 — 세부는 `.claude/rules/agent.md` 참고

## 5. 패키징 방침

`pyproject.toml` 없음 — 폴더 구조 미확정 상태라 의도적으로 미룸. `PYTHONPATH=src python src/main.py <video>`로 실행.

## 6. 하지 말 것

- perception이 매 프레임 LLM을 호출하게 만들지 말 것
- LLM에게 이미지를 주지 말 것
- tool의 `run()` 안에서 판단 필드를 생산하지 말 것
- `schema.py`의 forbidden-field 방어를 우회/제거하지 말 것
- 트리거를 순간값 임계치 하나로 단순화하지 말 것
- action을 tool과 같은 디렉토리·인터페이스로 섞지 말 것
- perception/trigger를 `agent/` 밑으로 다시 넣지 말 것
- 최상위 loose 모듈에 표준 라이브러리 이름을 쓰지 말 것

**트리거 우선순위/재호출 계약이 명시돼 있지 않다.** `trigger/rules.py`는 세그먼트당 트리거를 surge→stagnation→hotspot→conflict 순서로 검사해 처음 매칭되는 것 하나만 반환한다 — 두 조건이 동시에 참이어도 하나만 기록된다(우선순위는 코드 순서가 암묵적으로 정한다). 또한 cooldown/episode 상태가 없어서, 같은 이상 상황이 여러 세그먼트 지속되면 매 세그먼트 agent가 재호출된다. 이 동작을 바꾸려면(우선순위 명시, cooldown 추가 등) 먼저 "트리거를 이벤트로 볼지 상태로 볼지"부터 정의할 것 — 새 트리거를 추가하며 이 계약을 암묵적으로 더 복잡하게 만들지 말 것.

## 3. perception = observations, LLM = judgment

이 경계가 시스템 전체를 지탱한다. 위반하면 LLM이 도구를 우회해 직접 카운팅하는 문제(과거 시스템에서 실제로 발생: 가시 인원 ~15명인데 track 42개 보고)가 재발한다.

(과거엔 "tools = facts, LLM = judgment"를 슬로건으로 썼다. 설계 철학으로는 여전히 유효하지만, `agent/tools/`가 비어있는 상태에서 "tools"가 좁은 의미(`agent/tools/`)와 넓은 의미(perception 코드 포함)로 매번 갈려서 헷갈렸다. 지금 LLM 입력을 실제로 만드는 주체는 perception이므로 슬로건을 `perception = observations, LLM = judgment`로 바꿨다. 향후 tool-use가 복원되면 `perception computes observations, tools selectively expose evidence, LLM produces judgment`로 확장한다.)

- LLM은 **텍스트/숫자만** 입력받는다. 이미지·픽셀은 절대 LLM에 전달하지 않는다 (`agent/loop.py`의 `_facts_to_text`가 지금은 유일한 입력 경로 — tool-use 루프가 제거된 동안만 유효한 말이다. `TOOL_ONLY`가 채워져 tool 루프가 복원되면 tool 반환값도 입력 경로가 되므로, 그때 이 문장도 같이 갱신할 것). VLM을 쓰지 않는 이유가 이것이다 — 텍스트 전용 입력은 우회 가능성을 구조적으로 차단하는 장치지, 단순한 비용 절감이 아니다.
- LLM 출력 스키마(`agent/schema.py`의 `REQUIRED_FIELDS`)에는 `total_people` 같은 숫자 카운트 필드가 없다. 이런 필드는 **코드가 perception 관측값에서 직접 주입**한다 (`loop.py`의 `validated["total_people"] = facts.current.total`). `schema.validate()`는 LLM이 몰래 숫자 필드를 생산해도 `_FORBIDDEN_NUMERIC`으로 걷어낸다 — 이 방어를 제거하지 말 것. **단, 이 방어는 구조화 필드에만 적용된다.** `reasoning`은 자유 텍스트라 LLM이 그 안에 "약 30명이…" 같은 틀린 숫자를 재서술하는 것까지는 막지 못한다 — 알려진 한계로 남아있다.
- `tool_raw`는 (tool이 다시 생기면) 호출 원본을 그대로 보존한다 (연구용). 요약하거나 버리지 않는다.
- 새 tool을 추가할 때: `run(facts, **kwargs) -> dict`는 반드시 관측값만 반환해야 하고, 그 안에서 판단(assessment, action 등)을 생산하면 안 된다. 판단은 LLM의 몫이다.

### 노출 레지스트리 (`datatypes.py`)

`PerceptionResult`/`AggregatedFacts`의 각 필드를 LLM에게 어떤 경로로 보여줄지는 `datatypes.py`의 `ALWAYS_VISIBLE` / `TOOL_ONLY` / `NOT_EXPOSED` 세 집합이 유일하게 결정한다. 세 집합은 서로 배타적이며(assert로 강제), 필드마다 정확히 하나에만 속한다.

이전에는 이 판단이 `track_people` tool 안, `_facts_to_text` 안 등 코드 곳곳에 흩어져 즉흥적으로 결정되고 반복적으로 뒤집혔다. 새 perception 필드를 추가할 때는 반드시 이 레지스트리에 먼저 등록할 것 — `loop.py`나 tool 파일 안에서 개별적으로 노출 여부를 판단하지 말 것. `ALWAYS_VISIBLE`/`TOOL_ONLY` 분류 기준(매번 필요한 aggregate vs 가끔만 필요한 granular)은 이 레지스트리가 자동으로 답을 주지 않는다 — 여전히 사람 판단이 필요하다. `NOT_EXPOSED`는 애초에 판단 입력이 아닌 로깅/연구용 필드(`tracks`, `cv_elapsed_sec`, `timestamp`)다.

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

**지금 `action` 필드는 실행된 행동이 아니라 LLM이 생산한 권고값이다.** `main.py`는 `agent_output`을 받아 출력·저장만 하고 실제로 실행(dispatch)하지 않으며, `action/` 디렉토리는 아직 없다. 나중에 관리자 알림, 티켓 생성, 외부 시스템 제어 요청 등 도메인 부수효과가 필요해지면 `action/base.py`(Action ABC), `action/registry.py`(`@register` + `ACTIONS`), `action/dispatcher.py`(`assessment["action"]` 필드를 보고 해당 Action 실행)로 구성하고, `perception`/`trigger`/`agent`와 동등한 `src/` 최상위 형제로 둔다. `agent/` 안에 두지 말 것 — 결정(judgment)과 실행(effect)도 사실↔판단 분리의 연장이다.

`session.json`/`results.jsonl` 기록(`io_utils/session.py`)은 action 예시가 아니다 — 이미 존재하는 관측성·재현성 인프라(pipeline infrastructure)이지, 판정 이후 실행되는 도메인 부수효과가 아니다. 둘을 같은 범주로 묶지 말 것.

### LLM 프로바이더도 같은 registry 패턴

`agent/providers/`는 tool과 같은 원칙(기존 파일 수정 없이 파일 하나 추가 + registry 등록)을 LLM 벤더 선택에 적용한 것이다. `config.AGENT_PROVIDER`(`"anthropic"` | `"gemini"`) 값으로 `agent/providers/__init__.py`의 `_PROVIDERS` dict에서 클래스를 고른다. 다만 tool과 달리 **상속 인터페이스가 아니라 duck-typing**이다 — `init_state`/`send`/`extract_text`/`extract_usage`/`is_retryable` 5개 메서드만 구현하면 되고, `agent/loop.py`는 어떤 프로바이더가 붙었는지 전혀 모른다. 새 프로바이더 추가 시 `agent/loop.py`를 건드리지 말 것 — 그 순간 이 패턴이 깨진다.

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