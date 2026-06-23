# CongestAgent

LLM(Claude)을 두뇌로, YOLOv8을 손발로 사용하는 영상 혼잡도 분석 에이전트.

## 구조

```
CongestAgent/
├── requirements.txt
└── agent_system/
    ├── main.py           # 진입점
    ├── agent/            # 두뇌: ClaudeAgent (도메인 중립)
    ├── tools/            # 손발: YOLOv8 사람 카운팅
    ├── domains/          # 도메인 설정 (혼잡도 판단 기준 + 사용 도구)
    └── utils/            # 공통 유틸 (동영상 샘플링, 콘솔 출력)
```

## 동작 원리

```
프레임 이미지
    ↓
Claude (두뇌) ──── count_people 도구 호출 ────→ YOLOv8 (손발)
    ↑                                                ↓
    └──────────── 사람 수(정수) ←────────────────────┘
    ↓
[YOLO 카운트] + [장면 맥락 직접 관찰] → 혼잡도 종합 판단
    ↓
{ people_count, congestion_level, reasoning, action }
```

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일 생성:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## 실행

```bash
# 기본 실행 (5초 간격, opus 모델)
python agent_system/main.py --video sample.mp4

# 옵션 지정
python agent_system/main.py --video sample.mp4 --interval 10 --model sonnet
```

### 옵션

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--video` | (필수) | 분석할 동영상 파일 경로 |
| `--interval` | `5` | 프레임 샘플링 간격 (초) |
| `--model` | `opus` | 사용할 모델: `opus` / `sonnet` / `haiku` |
| `--domain` | `congestion` | 분석 도메인 |

## 출력

콘솔에 프레임별 결과를 출력하고, `results.json`으로 저장.

```
[ 10.0초] 분석 중...
    → 도구 호출: count_people
    ← 결과    : {'count': 7}
  혼잡도  : 🟡 MEDIUM
  인원수  : 7명
  조치    : monitor
  근거    : 좁은 복도에 7명이 밀집되어 있어 이동에 불편이 예상됨
```

## 도메인/도구 확장

새 도메인 추가: `agent_system/domains/` 에 모듈 작성 후 `__init__.py` 레지스트리에 등록.

새 도구 추가: `agent_system/tools/` 에 `BaseTool` 상속 클래스 작성.

두뇌(`agent/`) 코드는 수정 불필요.
## Web UI

터미널 출력 대신 브라우저에서 영상을 업로드하고 결과를 확인하려면:

```bash
python agent_system/web.py
```

브라우저에서 `http://127.0.0.1:8000`을 열면 됩니다. 분석 결과 JSON은 `results/`에, 업로드 영상은 `uploads/`에 저장됩니다.
# LLMAgentSystem

## Current structure

```text
LLMAgentSystem/
  agent_system/      # pure agent core
    agent/           # domain-neutral ClaudeAgent brain
    tools/           # measurable fact tools
    domains/         # domain prompts and injected tool sets
    main.py          # CLI entrypoint
  web/               # demo web layer
    web.py           # Flask server importing agent_system
    frontend/
      index.html
      app.js
      styles.css
  logs/
  requirements.txt
```

## CLI

```bash
python agent_system/main.py --video sample.mp4 --interval 5 --domain congestion
```

The CLI loads a domain config, injects `system_prompt` and `tools` into the domain-neutral `ClaudeAgent`, splits the video into interval segments, then lets Claude decide whether to call `track_people`.

## Web demo

```bash
python web/web.py
```

Open `http://127.0.0.1:8000`. The web layer is only a demo wrapper and imports the agent core.
