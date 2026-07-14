// vite.config.js의 outputs-api 미들웨어(/api/sessions*)를 통해 고정 루트
// (outputs/, io_utils/session.py의 OUTPUTS_DIR)를 읽는다. 브라우저 파일시스템
// 권한이 필요 없다 — 어떤 브라우저/webview에서도 동일하게 동작한다.
// `npm run dev`에서만 동작한다(vite build/preview에는 미들웨어가 없다).

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error || `${path} 요청 실패 (${res.status})`);
  }
  return res.json();
}

export async function fetchSessions() {
  return fetchJson('/api/sessions');
}

export async function fetchSessionMeta(sessionId) {
  return fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/meta`);
}

// results.jsonl을 줄 단위로 파싱한다. 실행 중인 세션은 마지막 줄이 쓰다 만
// 상태일 수 있으므로, 줄 단위로 파싱하고 실패한 줄은 조용히 건너뛴다.
export async function fetchResultsEntries(sessionId) {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/results`);
  if (!res.ok) {
    throw new Error(`results.jsonl 요청 실패 (${res.status})`);
  }
  const text = await res.text();
  const entries = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      entries.push(JSON.parse(trimmed));
    } catch {
      continue;
    }
  }
  return entries;
}
