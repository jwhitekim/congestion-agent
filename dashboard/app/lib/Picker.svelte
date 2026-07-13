<script>
  import { outputsHandle, sessions } from './stores.js';
  import {
    pickOutputsDirectory,
    listSessions,
    isFileSystemAccessSupported,
    isDragDropDirectorySupported,
    getDroppedDirectoryHandle,
  } from './fs.js';

  let error = $state('');
  let loading = $state(false);
  let dragging = $state(false);
  const supported = isFileSystemAccessSupported();
  // showDirectoryPicker와 별개 API라 따로 게이팅한다 — VS Code Simple Browser 같은
  // Electron webview는 supported=true여도 이건 false일 수 있다. false면 드래그앤드롭
  // UI 자체를 보여주지 않는다(버튼은 별개로 계속 동작).
  const dragDropSupported = isDragDropDirectorySupported();

  async function loadHandle(handle) {
    error = '';
    loading = true;
    try {
      const list = await listSessions(handle);
      outputsHandle.set(handle);
      sessions.set(list);
    } catch (e) {
      error = `폴더를 여는 중 오류가 발생했습니다: ${e.message}`;
    } finally {
      loading = false;
    }
  }

  async function handlePick() {
    let handle;
    try {
      handle = await pickOutputsDirectory();
    } catch (e) {
      if (e.name !== 'AbortError') {
        error = `폴더를 여는 중 오류가 발생했습니다: ${e.message}`;
      }
      return;
    }
    await loadHandle(handle);
  }

  function handleDragOver(e) {
    e.preventDefault();
    dragging = true;
  }

  function handleDragLeave() {
    dragging = false;
  }

  async function handleDrop(e) {
    e.preventDefault();
    dragging = false;
    try {
      const handle = await getDroppedDirectoryHandle(e.dataTransfer);
      await loadHandle(handle);
    } catch (e) {
      error = e.message;
    }
  }
</script>

<div
  class="picker"
  class:drop-zone={dragDropSupported}
  class:dragging
  role="region"
  aria-label={dragDropSupported ? 'outputs 폴더 드롭 영역' : undefined}
  ondragover={dragDropSupported ? handleDragOver : undefined}
  ondragleave={dragDropSupported ? handleDragLeave : undefined}
  ondrop={dragDropSupported ? handleDrop : undefined}
>
  <p>
    congestion-agent 실행 결과가 담긴 <code>outputs/</code> 폴더를 선택하세요{dragDropSupported ? ' (또는 이 영역에 드래그앤드롭)' : ''}.
  </p>

  {#if !supported}
    <p class="warn">
      이 브라우저는 File System Access API를 지원하지 않습니다. Chrome, Edge 등
      Chromium 계열 브라우저에서 열어주세요.
    </p>
  {:else}
    <button onclick={handlePick} disabled={loading}>
      {loading ? '불러오는 중...' : 'outputs 폴더 선택'}
    </button>
    {#if dragDropSupported}
      <p class="hint">또는 폴더를 이 영역에 끌어다 놓으세요</p>
    {:else}
      <p class="hint">
        이 브라우저(예: VS Code 내장 브라우저)는 드래그앤드롭을 지원하지 않을 수 있습니다 —
        버튼을 사용해주세요.
      </p>
    {/if}
  {/if}

  {#if error}<p class="error">{error}</p>{/if}
</div>
