<script>
  import { outputsHandle, selectedSession } from './lib/stores.js';
  import Picker from './lib/Picker.svelte';
  import SessionList from './lib/SessionList.svelte';
  import SessionDetail from './lib/SessionDetail.svelte';
</script>

<main>
  <h1>혼잡도 에이전트 대시보드</h1>

  {#if $outputsHandle === null}
    <Picker />
  {:else if $selectedSession === null}
    <SessionList />
  {:else}
    {#key $selectedSession.session_id}
      <SessionDetail session={$selectedSession} />
    {/key}
  {/if}
</main>
