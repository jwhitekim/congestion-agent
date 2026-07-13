// File System Access API 래퍼. 백엔드 없이 브라우저에서 로컬 outputs/ 폴더를 직접 읽는다.
// 아무 것도 캐시하지 않는다 — 항상 디스크에서 다시 읽는다.

export function isFileSystemAccessSupported() {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
}

// showDirectoryPicker와 별개 API다 — VS Code Simple Browser 같은 Electron
// webview는 showDirectoryPicker는 지원하면서 드래그앤드롭 항목을
// FileSystemHandle로 바꿔주는 이 메서드는 구현하지 않는 경우가 있다.
// prototype에 정적으로 존재하는지만 확인한다(런타임에 실제로 동작하는지는
// 드롭해봐야 알 수 있지만, 최소한 아예 없는 환경에서 드래그앤드롭 UI 자체를
// 보여주지 않기 위한 사전 게이팅용).
export function isDragDropDirectorySupported() {
  return (
    isFileSystemAccessSupported() &&
    typeof DataTransferItem !== 'undefined' &&
    'getAsFileSystemHandle' in DataTransferItem.prototype
  );
}

export async function pickOutputsDirectory() {
  return await window.showDirectoryPicker();
}

// 드래그앤드롭된 DataTransfer에서 디렉토리 핸들을 얻는다.
//
// items[0]을 바로 쓰지 않는다 — 실제 드래그에는 kind==='file'인 항목 외에
// kind==='string'인 부가 항목(예: text/plain 폴백)이 같이 섞여 오는 경우가 흔하고,
// 그런 항목의 getAsFileSystemHandle()은 함수는 존재해도 undefined를 반환한다.
// kind==='file'인 항목을 직접 찾고, 반환된 handle이 falsy일 가능성도 방어한다.
export async function getDroppedDirectoryHandle(dataTransfer) {
  const items = dataTransfer.items ? Array.from(dataTransfer.items) : [];
  const fileItem = items.find(
    (item) => item.kind === 'file' && typeof item.getAsFileSystemHandle === 'function'
  );
  if (!fileItem) {
    throw new Error(
      '드래그앤드롭에서 폴더 정보를 읽지 못했습니다. VS Code Simple Browser 같은 ' +
      '내장 브라우저(Electron webview)는 이 기능을 지원하지 않는 경우가 있습니다 — ' +
      '아래 "outputs 폴더 선택" 버튼을 사용해주세요.'
    );
  }
  const handle = await fileItem.getAsFileSystemHandle();
  if (!handle || handle.kind !== 'directory') {
    throw new Error('폴더를 드롭해주세요 (파일은 지원하지 않습니다).');
  }
  return handle;
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
