<script>
  import { sessions, selectedSession } from './stores.js';
  import { fetchSessions } from './api.js';

  let refreshing = $state(false);

  async function refresh() {
    refreshing = true;
    try {
      sessions.set(await fetchSessions());
    } finally {
      refreshing = false;
    }
  }

  function selectSession(s) {
    selectedSession.set(s);
  }
</script>

<div class="toolbar">
  <button onclick={refresh} disabled={refreshing}>
    {refreshing ? '새로고침 중...' : '새로고침'}
  </button>
</div>

{#if $sessions.length === 0}
  <div class="empty-state">
    <h2>세션 없음</h2>
    <p>outputs/ 폴더에 저장된 실행 결과가 없습니다.</p>
  </div>
{:else}
  <div class="section-head session-list-head">
    <h3>세션 목록</h3>
    <span>{$sessions.length} sessions</span>
  </div>
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
            <span class="badge done">완료</span>
          {:else}
            <span class="badge running"><span class="status-dot"></span>실행 중</span>
          {/if}
          {#if s.segment_count !== undefined}
            <span class="segment-count">{s.segment_count}개 세그먼트</span>
          {/if}
        </div>
      </button>
    {/each}
  </div>
{/if}
