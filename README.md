# congestion-agent

실내 공간의 혼잡도를 실시간으로 감시하고, 이상 패턴이 감지될 때만 LLM 에이전트를 소환해 상황을 판정하는 시스템.

기존 Django 기반 혼잡도 분석 시스템(학부 캡스톤)을 training-free, prompting 기반 순수 Python 코드베이스로 리팩토링한 것.
설계 원칙과 아키텍처 경계는 [AGENTS.md](./AGENTS.md)를 먼저 읽을 것.

## 핵심 아이디어

```
perception (항상 실행)  →  trigger (항상 실행)  →  agent (트리거 시에만 소환)
YOLOv8m + OC-SORT           rule 기반 조건문           텍스트 전용 LLM 판정
+ Line Density               (변화율·지속시간 기반)
```

- **LLM은 카메라를 보지 않는다.** 모든 입력은 도구(코드)가 집계한 숫자/텍스트 사실이다.
- **LLM은 상시 감시자가 아니라 트리거로 소환되는 의사결정자다.** 매 세그먼트가 아니라 이상 패턴(surge/stagnation/hotspot)이 감지될 때만 호출된다.
- **tools = facts, LLM = judgment.** 숫자 카운트는 코드가 주입하고, LLM은 판단만 생산한다. 자세한 경계는 AGENTS.md 참고.
- **perception/trigger/agent는 형제 레이어다.** 어느 하나가 다른 하나에 종속되지 않는다. 자세한 위계는 AGENTS.md 1절 참고.

## 설치

현재 `pyproject.toml`은 없다 (폴더 구조가 안정되기 전까지 패키징은 의도적으로 미룸). 의존성만 설치한다:

```bash
pip install -r requirements.txt
```

`requirements.txt`에 `torch`, `ultralytics`(YOLOv8), `ocsort`가 포함돼 있어 GPU 환경(CUDA)을 권장한다.
YOLO 모델 가중치는 `models/capdi-y8m-640-crowdah-v1-fp32-pt-20250609.pt` 경로에 위치해야 한다 (`config.MODEL_DIR`, `config.YOLO_MODEL_NAME`).

`ANTHROPIC_API_KEY` 환경변수가 필요하다 (agent 판정에 `anthropic` SDK 사용, 모델: `claude-sonnet-4-6`).

## 실행

패키지 설치 없이 `src/`를 `PYTHONPATH`에 직접 넣어 실행한다:

```bash
PYTHONPATH=src python src/main.py videos/supermarket.mp4
```

세그먼트마다 터미널에 PERCEPTION / TRIGGER / AGENT 3줄이 출력되고, 실행마다 `outputs/<timestamp>/` 세션 폴더가 새로 생성된다. `session.json`에는 세션 메타데이터(시작/종료 시각, config snapshot)가 기록되고, 세그먼트별 결과는 `results.jsonl`에 한 줄씩 즉시 append된다 (트리거 안 걸린 세그먼트도 `agent: null`로 포함, tool_raw 등 연구용 원본 데이터 보존).

결과 시각화 대시보드는 [`dashboard/`](./dashboard) 참고.

## 디렉토리 구조

```
src/
├── main.py                 파이프라인 오케스트레이션 (perception→trigger→agent)
├── config.py                공용 설정 — 모든 임계값·모델 경로·존 정의
├── datatypes.py               공용 dataclass: PerceptionResult, AggregatedFacts
├── perception/               perception 레이어 (LLM 없음, 상시 실행)
│   ├── detector.py              YOLO 추론
│   ├── tracker.py                OC-SORT 래퍼
│   ├── density.py                 Line Density, 평균 속도 계산
│   └── pipeline.py                 프레임 스트림 → PerceptionResult 스트림
├── trigger/                  trigger 레이어 (rule 기반 게이팅)
│   ├── history.py               SegmentHistory 링버퍼 (변화율/추세 기준값)
│   └── rules.py                   트리거 판정 (surge/stagnation/hotspot)
├── agent/                    agent 레이어 (LLM, 트리거 시에만 동작)
│   ├── loop.py                    LLM tool-use 루프
│   ├── prompt.py                   system prompt
│   ├── schema.py                    LLM 출력 검증 + 금지 필드(숫자 카운트) 제거
│   └── tools/                        LLM이 호출하는 도구 (registry 자동 등록)
│       └── track_people.py             구역/지표별 정밀 사실 반환
└── io_utils/
    ├── sampler.py                  영상 → 프레임 스트림
    └── reporter.py                  터미널 출력 (rich)
```

perception, trigger, agent, io_utils는 `src/` 밑에 형제로 위치한다 — 어느 것도 다른 것 밑에 종속되지 않는다. 각 레이어가 왜 이 위계여야 하는지는 AGENTS.md 1절 참고.

## 트리거 조건 (`config.py`)

| 트리거     | 조건                                                                 |
| ---------- | -------------------------------------------------------------------- |
| surge      | density가 직전 이동평균의 `SURGE_RATIO`(1.4)배 초과                  |
| stagnation | 평균 속도가 `SPEED_MIN`(0.5px/s) 미만으로 `STAG_SEC`(10초) 이상 지속 |
| hotspot    | 한 구역 인원이 `ZONE_MAX`(8명) 초과                                  |

세 조건 모두 순간값이 아니라 변화율 또는 지속시간을 기준으로 한다.

### 임계값 보정

`scripts/calibrate.py`가 영상의 density 분포를 percentile로 계산해 `DENSITY_LOW`/`DENSITY_HIGH` 제안값을 산출하는 스크립트였으나, 현재 `scripts/` 디렉토리는 리포에 없다. 필요하면 다시 추가한다.

## 현재 상태 / 미구현

- LLM 판단(`assessment.action`) 이후 실제로 알림·로깅 등을 실행하는 **action 레이어는 아직 없다.** 현재는 판정 결과를 출력·저장만 한다. 설계는 AGENTS.md 4절 참고.
- `agent/tools/`에는 `track_people` 하나만 등록되어 있다.
- **패키징 미결정.** `pyproject.toml` 없이 `PYTHONPATH` 방식으로 실행 중. 구조가 안정되면 다시 붙일 예정.
- **트리거 알고리즘의 위상 미결정.** 지금의 rule 기반 게이팅(변화율/지속시간)을 단순 엔지니어링 스캐폴딩으로 볼지, "언제 LLM을 부를지 판단하는 것" 자체를 연구 기여 지점으로 승격할지 아직 결정하지 않았다.
- 실시간 모니터링 vs. 사후 분석 리포트, 이 시스템의 최종 정체성은 아직 미정.

## 하드웨어

TITAN X Pascal 12GB / V100 32GB × 2 환경에서 개발. Fine-tuning 없이 순수 prompting 기반 접근만 사용한다.
