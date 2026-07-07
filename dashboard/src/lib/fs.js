// File System Access API 래퍼. 백엔드 없이 브라우저에서 로컬 outputs/ 폴더를 직접 읽는다.
// 아무 것도 캐시하지 않는다 — 항상 디스크에서 다시 읽는다.

export function isFileSystemAccessSupported() {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

export async function pickOutputsDirectory() {
  return await window.showDirectoryPicker();
}

async function readJsonFile(dirHandle, filename) {
  const fileHandle = await dirHandle.getFileHandle(filename);
  const file = await fileHandle.getFile();
  const text = await file.text();
  return JSON.parse(text);
}

// outputsHandle 바로 아래의 각 세션 폴더를 순회하며 session.json을 읽는다.
// session.json이 없거나 파싱에 실패하는 폴더(세션 폴더가 아님)는 건너뛴다.
export async function listSessions(outputsHandle) {
  const result = [];
  for await (const [, handle] of outputsHandle.entries()) {
    if (handle.kind !== 'directory') continue;
    try {
      const meta = await readJsonFile(handle, 'session.json');
      result.push({ ...meta, dirHandle: handle });
    } catch {
      continue;
    }
  }
  result.sort((a, b) => b.session_id.localeCompare(a.session_id));
  return result;
}

export async function readSessionMeta(dirHandle) {
  return await readJsonFile(dirHandle, 'session.json');
}

// results.jsonl을 읽어 파싱한다. 실행 중인 세션은 마지막 줄이 쓰다 만 상태일 수 있으므로
// 줄 단위로 JSON.parse하고, 실패한 줄은 조용히 건너뛴다.
export async function readResultsEntries(dirHandle) {
  const fileHandle = await dirHandle.getFileHandle('results.jsonl');
  const file = await fileHandle.getFile();
  const text = await file.text();
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

export async function getResultsLastModified(dirHandle) {
  const fileHandle = await dirHandle.getFileHandle('results.jsonl');
  const file = await fileHandle.getFile();
  return file.lastModified;
}
