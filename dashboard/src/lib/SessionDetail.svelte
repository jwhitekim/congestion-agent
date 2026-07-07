<script>
  import { onMount, onDestroy } from 'svelte';
  import { Chart } from 'chart.js/auto';
  import { selectedSession } from './stores.js';
  import { readSessionMeta, readResultsEntries, getResultsLastModified } from './fs.js';

  let { session } = $props();

  let meta = $state(null);
  let entries = $state([]);
  let loadError = $state('');

  let lastModified = null;
  let pollId = null;

  let seriesCanvas = $state();
  let latencyCanvas = $state();
  let seriesChart = null;
  let latencyChart = null;

  const TRIGGER_LABELS = { surge: 'surge', stagnation: 'stagnation', hotspot: 'hotspot' };
  const TRIGGER_COLORS = { surge: '#e5484d', stagnation: '#f5a623', hotspot: '#8e4ec6' };

  // ── 파생 통계 (카드 4개) ──
  let totalSegments = $derived(entries.length);
  let triggeredEntries = $derived(entries.filter((e) => e.agent !== null && e.agent !== undefined));
  let triggerCount = $derived(triggeredEntries.length);
  let latencies = $derived(
    triggeredEntries
      .map((e) => e.agent.agent_elapsed_sec)
      .filter((v) => typeof v === 'number')
  );
  let avgLatency = $derived(
    latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : null
  );
  let p95Latency = $derived(percentile(latencies, 0.95));

  function percentile(values, p) {
    if (values.length === 0) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const idx = Math.min(sorted.length - 1, Math.floor(p * sorted.length));
    return sorted[idx];
  }

  function fmtSec(v) {
    return typeof v === 'number' ? `${v.toFixed(3)}s` : '-';
  }

  async function loadAll() {
    try {
      meta = await readSessionMeta(session.dirHandle);
      entries = await readResultsEntries(session.dirHandle);
      lastModified = await getResultsLastModified(session.dirHandle);
      loadError = '';
      renderCharts();
      if (!meta.ended_at) startPolling();
    } catch (e) {
      loadError = `데이터를 읽는 중 오류가 발생했습니다: ${e.message}`;
    }
  }

  async function pollTick() {
    try {
      const freshMeta = await readSessionMeta(session.dirHandle);
      const current = await getResultsLastModified(session.dirHandle);
      if (current !== lastModified) {
        lastModified = current;
        entries = await readResultsEntries(session.dirHandle);
        renderCharts();
      }
      meta = freshMeta;
      if (freshMeta.ended_at) {
        stopPolling();
      }
    } catch (e) {
      loadError = `데이터를 읽는 중 오류가 발생했습니다: ${e.message}`;
    }
  }

  function startPolling() {
    stopPolling();
    pollId = setInterval(pollTick, 1000);
  }

  function stopPolling() {
    if (pollId !== null) {
      clearInterval(pollId);
      pollId = null;
    }
  }

  function renderCharts() {
    renderSeriesChart();
    renderLatencyChart();
  }

  function renderSeriesChart() {
    if (!seriesCanvas) return;

    const densityPoints = entries.map((e) => ({ x: e.timestamp, y: e.perception.density }));
    const speedPoints = entries.map((e) => ({ x: e.timestamp, y: e.perception.avg_speed }));
    const triggerDatasets = Object.keys(TRIGGER_LABELS).map((type) => ({
      label: TRIGGER_LABELS[type],
      type: 'scatter',
      data: entries
        .filter((e) => e.trigger === type)
        .map((e) => ({ x: e.timestamp, y: e.perception.density })),
      backgroundColor: TRIGGER_COLORS[type],
      borderColor: TRIGGER_COLORS[type],
      pointStyle: 'triangle',
      pointRadius: 7,
      pointHoverRadius: 9,
      showLine: false,
      yAxisID: 'yDensity',
    }));

    const data = {
      datasets: [
        {
          label: 'density',
          data: densityPoints,
          borderColor: '#3b82f6',
          backgroundColor: '#3b82f6',
          yAxisID: 'yDensity',
          tension: 0.2,
          pointRadius: 2,
        },
        {
          label: 'avg_speed',
          data: speedPoints,
          borderColor: '#10b981',
          backgroundColor: '#10b981',
          yAxisID: 'ySpeed',
          tension: 0.2,
          pointRadius: 2,
        },
        ...triggerDatasets,
      ],
    };

    if (seriesChart) {
      seriesChart.data = data;
      seriesChart.update();
      return;
    }

    seriesChart = new Chart(seriesCanvas, {
      type: 'line',
      data,
      options: {
        parsing: false,
        animation: false,
        scales: {
          x: { type: 'linear', title: { display: true, text: 'timestamp (s)' } },
          yDensity: { type: 'linear', position: 'left', title: { display: true, text: 'density' } },
          ySpeed: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: 'avg_speed (px/s)' },
            grid: { drawOnChartArea: false },
          },
        },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function renderLatencyChart() {
    if (!latencyCanvas) return;

    const points = triggeredEntries
      .filter((e) => typeof e.agent.agent_elapsed_sec === 'number')
      .map((e) => ({ x: e.timestamp, y: e.agent.agent_elapsed_sec }));

    const data = {
      datasets: [
        {
          label: 'agent_elapsed_sec',
          data: points,
          borderColor: '#f97316',
          backgroundColor: '#f97316',
          tension: 0.2,
          pointRadius: 3,
        },
      ],
    };

    if (latencyChart) {
      latencyChart.data = data;
      latencyChart.update();
      return;
    }

    latencyChart = new Chart(latencyCanvas, {
      type: 'line',
      data,
      options: {
        parsing: false,
        animation: false,
        scales: {
          x: { type: 'linear', title: { display: true, text: 'timestamp (s)' } },
          y: { type: 'linear', title: { display: true, text: 'latency (sec)' } },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  function goBack() {
    selectedSession.set(null);
  }

  onMount(() => {
    loadAll();
  });

  onDestroy(() => {
    stopPolling();
    seriesChart?.destroy();
    latencyChart?.destroy();
  });
</script>

<div class="toolbar">
  <button class="secondary" onclick={goBack}>← 목록으로</button>
  {#if meta && !meta.ended_at}
    <span class="badge running">🔴 실행 중 (1초마다 자동 갱신)</span>
  {/if}
</div>

{#if loadError}
  <p class="error">{loadError}</p>
{/if}

{#if meta}
  <h2>{meta.session_id}</h2>
  <p class="video-path">{meta.video_path}</p>

  <div class="cards">
    <div class="card">
      <div class="card-label">총 세그먼트 수</div>
      <div class="card-value">{totalSegments}</div>
    </div>
    <div class="card">
      <div class="card-label">트리거 발생 횟수</div>
      <div class="card-value">{triggerCount}</div>
    </div>
    <div class="card">
      <div class="card-label">agent 평균 latency</div>
      <div class="card-value">{fmtSec(avgLatency)}</div>
    </div>
    <div class="card">
      <div class="card-label">agent p95 latency</div>
      <div class="card-value">{fmtSec(p95Latency)}</div>
    </div>
  </div>

  <div class="chart-wrap">
    <canvas bind:this={seriesCanvas}></canvas>
  </div>

  <div class="chart-wrap">
    <canvas bind:this={latencyCanvas}></canvas>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>timestamp</th>
          <th>trigger</th>
          <th>assessment</th>
          <th>congestion_level</th>
          <th>action</th>
          <th>agent_elapsed_sec</th>
          <th>api_round_trips</th>
        </tr>
      </thead>
      <tbody>
        {#each entries as e (e.timestamp)}
          <tr>
            <td>{e.timestamp}</td>
            <td>{e.trigger ?? '-'}</td>
            <td>{e.agent?.assessment ?? '-'}</td>
            <td>{e.agent?.congestion_level ?? '-'}</td>
            <td>{e.agent?.action ?? '-'}</td>
            <td>{e.agent?.agent_elapsed_sec ?? '-'}</td>
            <td>{e.agent?.api_round_trips ?? '-'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}
