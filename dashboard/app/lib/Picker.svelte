<script>
  import { outputsHandle, sessions } from './stores.js';
  import {
    pickOutputsDirectory,
    listSessions,
    isFileSystemAccessSupported,
    getDroppedDirectoryHandle,
  } from './fs.js';

  let error = $state('');
  let loading = $state(false);
  let dragging = $state(false);
  const supported = isFileSystemAccessSupported();

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
    if (supported) dragging = true;
  }

  function handleDragLeave() {
    dragging = false;
  }

  async function handleDrop(e) {
    e.preventDefault();
    dragging = false;
    if (!supported) return;
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
  class:dragging
  role="region"
  aria-label="outputs 폴더 드롭 영역"
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
>
  <p>
    congestion-agent 실행 결과가 담긴 <code>outputs/</code> 폴더를 선택하거나
    이 영역에 드래그앤드롭하세요.
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
    <p class="hint">또는 폴더를 이 영역에 끌어다 놓으세요</p>
  {/if}

  {#if error}<p class="error">{error}</p>{/if}
</div>
