<script>
  import { outputsHandle, sessions, selectedSession } from './stores.js';
  import { listSessions } from './fs.js';

  let refreshing = $state(false);

  async function refresh() {
    refreshing = true;
    try {
      sessions.set(await listSessions($outputsHandle));
    } finally {
      refreshing = false;
    }
  }

  function selectSession(s) {
    selectedSession.set(s);
  }

  function chooseAnotherFolder() {
    outputsHandle.set(null);
    sessions.set([]);
  }
</script>

<div class="toolbar">
  <button onclick={refresh} disabled={refreshing}>
    {refreshing ? '새로고침 중...' : '새로고침'}
  </button>
  <button class="secondary" onclick={chooseAnotherFolder}>다른 폴더 선택</button>
</div>

{#if $sessions.length === 0}
  <p>선택한 폴더에 세션이 없습니다.</p>
{:else}
  <div class="session-list">
    {#each $sessions as s (s.session_id)}
      <button
        type="button"
        class="session-item"
        onclick={() => selectSession(s)}
      >
        <div class="session-main">
          <span class="session-id">{s.session_id}</span>
          <span class="video-path">{s.video_path}</span>
        </div>
        <div class="session-meta">
          {#if s.ended_at}
            <span class="badge done">✅ 완료</span>
          {:else}
            <span class="badge running">🔴 실행 중</span>
          {/if}
          {#if s.segment_count !== undefined}
            <span class="segment-count">{s.segment_count}개 세그먼트</span>
          {/if}
        </div>
      </button>
    {/each}
  </div>
{/if}
