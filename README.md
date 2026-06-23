# LLMAgentSystem

LLM(두뇌 역할, Claude)이 판단하고, CV 도구(손발 역할)가 측정하는 영상 혼잡도 분석 에이전트 시스템.

## 구조

```
LLMAgentSystem/
  agent_system/
    agent/           # LLM 층: ClaudeAgent (도메인 중립, tool-use 루프만 담당)
    tools/           # 도구(손발 역할): 사실 측정만. 판단 안 함
      detection/     # YOLOv8 탐지
      track_people_tool.py
      bytetrack_adapter.py
    domains/         # 도메인 설정: 시스템 프롬프트 + 도구 묶음
    utils/           # video.py(프레임 추출), display.py, custom_logger.py
    main.py          # CLI 진입점
  web/               # 데모용 웹 레이어 (agent_system import해서 씀)
    web.py
    frontend/
  logs/
  requirements.txt
```

## 동작 원리

```
main.py / web.py
  ↓  build_vision_content()  ← 구간 메타 + 샘플 프레임 (도메인 중립)
ClaudeAgent.run(content)
  ↓  LLM(두뇌 역할)이 프레임을 보고 판단
  └─ 필요하다고 판단되면 → track_people 도구 호출
                              ↓ YOLO 탐지 + ByteTrack 추적
                              ↓ 위치·bbox·구역 인원수 반환 (사실만)
  ↓  LLM이 분포를 해석해 최종 판단
{ total_people, distribution_summary, congestion_level, local_hotspots, reasoning, action }
```

핵심: LLM이 도구를 먼저 다 돌리지 않는다. 프레임을 본 뒤 필요하면 스스로 호출한다.

## 설치

```bash
pip install -r requirements.txt
```

`supervision`의 ByteTrack을 사용한다 (`pip install supervision` 포함).

## 환경 변수

프로젝트 루트에 `.env` 파일 생성:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## 실행

### CLI

```bash
python agent_system/main.py --video sample.mp4
python agent_system/main.py --video sample.mp4 --interval 10 --model sonnet
```

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--video` | (필수) | 분석할 동영상 파일 경로 |
| `--interval` | `5` | 구간 길이 (초) |
| `--model` | `opus` | `opus` / `sonnet` / `haiku` |
| `--domain` | `congestion` | 분석 도메인 |

결과는 콘솔 출력 + `results.json` 저장.

### Web 데모

```bash
python web/web.py
```

`http://127.0.0.1:8000` 에서 영상 업로드 후 결과 확인. 결과 JSON은 `results/`, 업로드 영상은 `uploads/`에 저장.

## 도메인/도구 확장

- 새 도구: `tools/`에 `BaseTool` 상속 클래스 작성.
- 새 도메인: `domains/`에 `system_prompt + tools` 묶음 작성 후 `__init__.py` 레지스트리에 등록.
- `agent/` 코드는 수정 불필요.
