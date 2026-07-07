<script>
  import { outputsHandle, sessions } from './stores.js';
  import { pickOutputsDirectory, listSessions, isFileSystemAccessSupported } from './fs.js';

  let error = $state('');
  let loading = $state(false);
  const supported = isFileSystemAccessSupported();

  async function handlePick() {
    error = '';
    loading = true;
    try {
      const handle = await pickOutputsDirectory();
      const list = await listSessions(handle);
      outputsHandle.set(handle);
      sessions.set(list);
    } catch (e) {
      if (e.name !== 'AbortError') {
        error = `폴더를 여는 중 오류가 발생했습니다: ${e.message}`;
      }
    } finally {
      loading = false;
    }
  }
</script>

<div class="picker">
  <p>congestion-agent 실행 결과가 담긴 <code>outputs/</code> 폴더를 선택하세요.</p>

  {#if !supported}
    <p class="warn">
      이 브라우저는 File System Access API를 지원하지 않습니다. Chrome, Edge 등
      Chromium 계열 브라우저에서 열어주세요.
    </p>
  {:else}
    <button onclick={handlePick} disabled={loading}>
      {loading ? '불러오는 중...' : 'outputs 폴더 선택'}
    </button>
  {/if}

  {#if error}<p class="error">{error}</p>{/if}
</div>
