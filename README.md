# congestion-agent

저장된 실내 영상을 세그먼트 단위로 순차 분석하고, 이상 패턴이 감지된 세그먼트에만 LLM 판단을 적용하는 워크플로우다. 기존 Django 기반 혼잡도 분석 시스템(학부 캡스톤)을 training-free, prompting 기반 순수 Python 코드베이스로 리팩토링했다.

설계 원칙과 아키텍처 경계는 [AGENTS.md](./AGENTS.md)를 먼저 읽을 것 — 이 문서는 설치/실행 방법과 현재 구현 상태를 다룬다.

## 핵심 아이디어

이 시스템은 세 컴포넌트로 구성된다.

```
perception (항상 실행)  →  trigger (항상 실행)  →  LLM module (트리거 시에만 소환)
YOLOv8m + ByteTrack          rule 기반 조건문           텍스트 전용 LLM 판정
+ Line Density               (변화율·지속시간 기반)
```

- **perception = observations, LLM = judgment.** 사람 수, 밀도, 속도 등 관측값은 perception 코드가 계산하고, LLM은 그 관측값을 바탕으로 상황 판정과 권고 행동만 생성한다. LLM은 카메라를 직접 보지 않는다 — 모든 입력은 숫자/텍스트 관측값이다.
- **LLM은 상시 감시자가 아니라 트리거로 소환되는 상황 판정 모듈이다.** 매 세그먼트가 아니라 이상 이벤트(surge/stagnation/hotspot) 또는 규칙 간 상충 사례(conflict)가 감지될 때만 호출되고, 실제 행동을 집행하지 않고 권고값만 생산한다.
- **perception/trigger/agent는 코드 소유권상 형제 패키지다.** 어느 하나가 다른 하나 밑에 종속되지 않으며, 런타임에서는 `perception → trigger → agent`의 단방향 흐름을 이룬다.

> 과거엔 "tools = facts, LLM = judgment"를 슬로건으로 썼다. 지금은 `agent/tools/`가 비어있고 관측값을 실제로 만드는 주체가 perception이라, 대표 슬로건을 `perception = observations, LLM = judgment`로 바꿨다. 설계 철학과 향후 tool 복원 시 확장 방향은 AGENTS.md 3절 참고.

> "에이전트"는 리포 명칭(`congestion-agent`)에서 온 내부 통칭이다. NCISS 논문에서는 이 시스템을 자율 에이전트가 아니라 **workflow**로 분류한다(Anthropic 2024 taxonomy 기준 — 코드가 trigger·정보 흐름·실행 경로를 통제하고, LLM은 트리거 시에만 판단을 생산하는 국소적 추론 단계). 정확한 명칭은 **"이벤트 트리거형 에이전틱 워크플로우"(event-triggered agentic workflow)**로 확정했다(2026-07-15). 리포 내부 통칭과 논문의 시스템 분류는 다른 층위이므로 섞어 쓰지 말 것.

## 설치

```bash
pip install -r requirements.txt
make install   # dashboard/ npm 의존성 설치
```

`requirements.txt`는 CUDA 12.6 GPU 빌드 `torch`/`torchvision`을 설치한다(최신 드라이버도 하위 호환되므로 CUDA 13.0에서도 그대로 동작). `ultralytics`(YOLOv8), `supervision`(ByteTrack)이 포함돼 있어 GPU 환경(CUDA)을 권장한다. YOLO 모델 가중치는 `models/capdi-y8m-640-crowdah-v1-fp32-pt-20250609.pt` 경로에 위치해야 한다(`config.MODEL_DIR`, `config.YOLO_MODEL_NAME`). `make install`은 `npm --prefix dashboard install`만 실행하고 Python 의존성 설치는 안내만 한다 — GPU 빌드 선택이 걸린 설치라 자동 실행하지 않는다.

LLM 판정에는 `ANTHROPIC_API_KEY` 환경변수가 필요하다(`anthropic` SDK, 기본 모델: `claude-sonnet-4-6`, `ANTHROPIC_MODEL`로 override 가능). 실험적으로 Gemini도 지원한다 — `AGENT_PROVIDER=gemini`로 설정하면 `google-genai` SDK로 기본 `gemini-3.5-flash`(`GEMINI_MODEL`로 override 가능, `GEMINI_API_KEY` 필요)를 대신 호출한다. 두 프로바이더 모두 `agent/providers/`의 duck-typing 인터페이스(`init_state/send/extract_text/extract_usage/is_retryable`)만 구현하면 되므로, 새 프로바이더를 추가해도 `agent/loop.py`는 건드릴 필요가 없다.

API 호출은 네트워크/rate limit/서버 오류에 한해 지수 백오프로 자동 재시도한다(`config.AGENT_MAX_RETRIES`, 기본 3회). LLM 판단 자체의 재시도(self-correction)와는 무관하다.

## 실행

```bash
make run                                  # videos/department_store.mp4 (기본값)
make run VIDEO=videos/supermarket.mp4     # 다른 영상 지정
```

`make run`은 `PYTHONPATH=src python src/main.py $(VIDEO)`를 실행한다 — 패키지 설치 없이 `src/`를 `PYTHONPATH`에 직접 넣는 구조라 `make` 없이도 그 명령을 직접 쳐도 동일하다.

실행마다 `outputs/<timestamp>/` 세션 폴더가 새로 생성된다. `session.json`은 세션 메타데이터(시작/종료 시각, config snapshot)를, `results.jsonl`은 세그먼트별 결과를 한 줄씩 즉시 기록한다 — 트리거 안 걸린 세그먼트도 `agent: null`로 포함하고, 트리거가 걸렸다면 어떤 근거로 걸렸는지(`trigger_reason`, 예: `"density 22.9 > avg × 1.4, ratio=1.60"`)도 함께 남긴다. 단, `trigger_reason`은 로그·결과 파일에만 기록될 뿐 LLM 프롬프트에는 아직 주입하지 않는다 — 주입 시 판단 품질이 개선되는지는 검증 전이다. `tool_raw` 등 연구용 원본 데이터도 보존한다.

결과 시각화 대시보드는 [`dashboard/`](./dashboard) 참고.

```bash
make dash         # 개발 서버 (npm --prefix dashboard run dev)
make dash-build   # 정적 빌드 (npm --prefix dashboard run build)
```

대시보드는 폴더 선택/드래그앤드롭이 없다 — Vite dev 서버의 미들웨어(`vite.config.js`)가 고정 루트 `outputs/`(`io_utils/session.py`의 `OUTPUTS_DIR`)를 직접 읽어 `/api/sessions*`로 내려주고, 브라우저는 그걸 fetch만 한다. 브라우저 파일시스템 권한이 필요 없어 VS Code Simple Browser 같은 제한적 webview에서도 동일하게 동작한다. 세션이 아직 실행 중이면 1초 간격으로 자동 갱신한다. **`make dash-build`로 만든 정적 빌드에는 이 API가 없다** — `configureServer`는 dev 서버 전용이라 `vite preview`나 정적 배포에서는 세션 목록이 뜨지 않는다.

## 디렉토리 구조

```
src/
├── main.py                 파이프라인 오케스트레이션 (perception→trigger→agent)
├── config.py                공용 설정 — 모든 임계값·모델 경로·존 정의·AGENT_PROVIDER
├── datatypes.py               공용 dataclass(PerceptionResult, AggregatedFacts) +
│                                ALWAYS_VISIBLE/TOOL_ONLY/NOT_EXPOSED 노출 레지스트리
├── perception/               perception 컴포넌트 (LLM 없음, 상시 실행)
│   ├── detector.py              YOLO 추론
│   ├── tracker.py                ByteTrack 래퍼
│   ├── density.py                 Line Density, 평균 속도 계산
│   ├── zone_metrics.py             구역별 정규화 밀도 + 집중도(HHI) 계산
│   └── pipeline.py                 프레임 스트림 → PerceptionResult 스트림
├── trigger/                  trigger 컴포넌트 (rule 기반 게이팅)
│   ├── history.py               SegmentHistory 링버퍼 (변화율/추세 기준값)
│   └── rules.py                   트리거 판정 (surge/stagnation/hotspot/conflict)
├── agent/                    LLM 판정 (트리거 시에만 동작, single-shot, tool 없음)
│   ├── loop.py                    호출 오케스트레이션 + 재시도 + facts→텍스트 변환
│   ├── prompt.py                   system prompt
│   ├── schema.py                    LLM 출력 검증 + 금지 필드(숫자 카운트) 제거
│   ├── providers/                    프로바이더 registry (anthropic/gemini, duck-typing)
│   └── tools/                        현재 비어있음 — TOOL_ONLY가 채워지면 여기 추가
└── io_utils/
    ├── sampler.py                  영상 → 프레임 스트림
    ├── reporter.py                  터미널 출력 (rich)
    └── session.py                    outputs/<timestamp>/ 세션 폴더, session.json/results.jsonl 관리

scripts/
├── analyze_bottleneck.py     results.jsonl에서 agent 호출 왕복시간/토큰 상관관계 분석
└── probe_agent.py              합성 case로 LLM 출력이 입력에 따라 실제로 차별화되는지 확인
```

perception, trigger, agent, io_utils는 `src/` 밑에 형제로 위치하며 어느 것도 다른 것 밑에 종속되지 않는다 — 이 위계가 필요한 이유는 AGENTS.md 1절 참고. `agent/` 폴더는 에이전트 전체가 아니라 그중 LLM 판정 파트만 담는다.

`agent/tools/`는 지금 비어있다. `track_people` tool이 있었으나 `_facts_to_text`가 넘기는 정보와 완전히 중복돼(no-op) 삭제했다. 어떤 필드를 LLM에게 어떤 경로로 보여줄지는 `datatypes.py`의 노출 레지스트리 한 곳에서만 결정하며, tool은 `TOOL_ONLY`가 채워질 때만 다시 필요해진다.

## 트리거 조건 (`config.py`)

| 트리거     | 조건                                                                                          |
| ---------- | --------------------------------------------------------------------------------------------- |
| surge      | density가 직전 이동평균의 `SURGE_RATIO`(1.4)배 초과                                           |
| stagnation | 평균 속도가 `SPEED_MIN`(0.5px/s) 미만으로 `STAG_SEC`(10초) 이상 지속                          |
| hotspot    | 한 구역 인원이 `ZONE_MAX`(8명) 초과                                                           |
| conflict   | 순간값 기준 `level=low`인데 `density_slope`가 `CONFLICT_SLOPE_MIN`(0.4) 초과 — 순간값과 추세 판정이 상충하는 경계 사례 |

surge/stagnation은 변화율 또는 지속시간 기준이다. conflict는 "규칙 두 개가 서로 다른 결론을 낸다"는 것 자체가 트리거 조건이다 — surge는 직전 평균 대비 비율이라 완만하지만 꾸준한 상승은 못 잡고, level은 순간 density만 보므로 추세를 모른다. 이 경계 사례를 LLM에 넘겨 해석하게 하는 것이 conflict의 존재 이유다(`trigger/rules.py` 4번 조건 주석 참고).

**hotspot은 이 원칙의 유일한 예외다.** 다른 세 트리거와 달리 `zone_count > ZONE_MAX` 순간값만 보고 즉시 발동하며 지속시간 조건이 없다 — AGENTS.md 6절 "트리거를 순간값 임계치 하나로 단순화하지 말 것"과 문자 그대로는 어긋난다. 의도적 예외로 남길지 지속시간 조건을 추가할지 아직 결정하지 않았다.

**`density_slope`/`speed_trend`는 초당이 아니라 세그먼트당 선형회귀 기울기다**(`trigger/history.py`, x축이 시간이 아니라 세그먼트 인덱스). `CONFLICT_SLOPE_MIN=0.4`의 의미는 `SEGMENT_INTERVAL`(현재 5초)에 종속적이므로, `SEGMENT_INTERVAL`을 바꾸면 `CONFLICT_SLOPE_MIN`도 재보정해야 한다.

**트리거 우선순위와 반복 호출 계약이 명시돼 있지 않다.** `trigger/rules.py`는 세그먼트당 트리거를 surge→stagnation→hotspot→conflict 순서로 검사해 처음 매칭되는 것 하나만 반환한다 — 두 조건이 동시에 참이어도 하나만 기록되고, 우선순위는 코드 순서가 암묵적으로 정한다. 또한 cooldown이 없어서 같은 이상 상황이 여러 세그먼트 지속되면(예: hotspot 30초 유지) 매 세그먼트 LLM을 다시 호출한다 — "이상 패턴 감지 시에만 호출"이 이벤트당 1회가 아니라 이벤트 지속 중 반복 호출이라는 뜻이다. 논문에서 호출 비용/횟수를 주장할 때 이 부분을 먼저 확인해야 한다.

## 현재 상태 / 미구현

- **action 레이어가 없다.** `action` 필드는 실행된 행동이 아니라 LLM이 생산한 권고값이며, 현재는 판정 결과를 출력·저장만 한다. 설계는 AGENTS.md 4절 참고.
- **트리거 알고리즘의 위상 미결정.** rule 기반 게이팅을 단순 엔지니어링 스캐폴딩으로 볼지, "언제 LLM을 부를지 판단하는 것" 자체를 연구 기여 지점으로 승격할지 아직 결정하지 않았다. conflict 트리거 추가는 이 질문에 대한 답이 아니라 별개의 트리거를 더한 것뿐이다.
- **hotspot 순간값 문제, 트리거 우선순위/반복 호출 계약 부재** — 상세는 위 "트리거 조건" 절 참고. 둘 다 결정만 남았다.
- **Gemini 프로바이더는 실험적 상태다.** Sonnet/Haiku 레이턴시 비교 목적으로 추가했고, 정식 지원 대상인지는 미결정.
- **`reasoning` 필드의 숫자 hallucination은 스키마 방어 범위 밖이다.** `schema.py`가 `total_people` 같은 구조화 필드는 걸러내지만, LLM이 자유 텍스트 `reasoning`에 "약 30명이…" 같은 틀린 숫자를 재서술하는 것은 막지 못한다. 알려진 한계로 남겨둔 상태다.