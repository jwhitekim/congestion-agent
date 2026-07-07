# congestion-agent dashboard

`src/`(congestion-agent 파이프라인)가 `outputs/<timestamp>/`에 남기는 `session.json` / `results.jsonl`을 시각화하는 순수 프론트엔드 대시보드. 백엔드 서버가 없다 — 브라우저의 [File System Access API](https://developer.mozilla.org/en-US/docs/Web/API/File_System_Access_API)로 로컬 `outputs/` 폴더를 직접 읽는다.

## 실행

```bash
npm install
npm run dev
```

브라우저에서 안내된 주소(기본 `http://localhost:5173`)를 연다.

## 브라우저 제약

**Chrome, Edge 등 Chromium 계열 브라우저에서만 동작한다.** `showDirectoryPicker()`(File System Access API)는 Firefox, Safari에는 구현되어 있지 않다. 지원하지 않는 브라우저로 열면 첫 화면에서 안내 메시지만 표시된다.

## 사용법

1. 첫 화면에서 "outputs 폴더 선택" 클릭 → congestion-agent 실행 결과가 쌓인 `outputs/` 폴더(리포 루트 기준 `../outputs`)를 선택한다.
2. 세션 목록에서 원하는 세션을 클릭하면 상세 화면(요약 카드, 시계열 차트, latency 차트, 세그먼트 테이블)으로 이동한다.
3. 선택한 세션이 아직 실행 중(`session.json`의 `ended_at`이 `null`)이면 1초 간격으로 `results.jsonl`을 다시 읽어 화면을 자동 갱신한다. 세션이 끝나면 자동으로 갱신을 멈춘다.

데이터는 항상 디스크에서 다시 읽는다 — localStorage 등에 캐시하지 않는다.
