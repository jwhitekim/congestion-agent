// ── DOM 레퍼런스 ────────────────────────────────────────────────
const form = document.querySelector("#analysisForm");
const videoInput = document.querySelector("#videoInput");
const preview = document.querySelector("#preview");
const emptyState = document.querySelector("#emptyState");
const submitButton = document.querySelector("#submitButton");
const statusBadge = document.querySelector("#statusBadge");
const fileInfo = document.querySelector("#fileInfo");
const resultsSection = document.querySelector("#resultsSection");
const resultsMeta = document.querySelector("#resultsMeta");
const timelineStrip = document.querySelector("#timelineStrip");
const timelineLabels = document.querySelector("#timelineLabels");
const frameCards = document.querySelector("#frameCards");

let previewUrl = null;

// ── 상태 배지 ───────────────────────────────────────────────────
function setStatus(text, className) {
  statusBadge.textContent = text;
  statusBadge.className = `status-badge ${className}`;
}

// ── 시간 포맷 (utils/display.py:_fmt_time 과 동일 로직) ─────────
function fmtTime(sec) {
  const s = Math.floor(Number(sec) || 0);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

// ── 공유 요약 추출 (utils/display.py:summarize_frame 과 동일 로직) ─
// 한 곳만 고치면 카드 헤더와 타임라인 양쪽에 반영된다.
function summarizeFrame(record) {
  const segment = record.segment || {};
  const result = record.result || {};
  const error = record.error || null;
  const startSec = segment.start_sec ?? 0;
  const dist = result.distribution_summary || "";
  const distShort = dist.length > 24 ? dist.slice(0, 24) + "…" : dist;

  return {
    timestampLabel: fmtTime(startSec),
    startSec,
    totalPeople: error ? "ERR" : (result.total_people ?? "?"),
    congestionLevel: error ? null : (result.congestion_level || null),
    action: error ? null : (result.action || null),
    distributionShort: error ? String(error) : distShort,
    error,
  };
}

// ── 액션 레이블 ─────────────────────────────────────────────────
function actionLabel(action) {
  return { none: "none", monitor: "⚠ monitor", alert: "🚨 alert" }[action] || (action || "-");
}

// ── 타임라인 띠 렌더링 ──────────────────────────────────────────
function buildTimeline(segments) {
  timelineStrip.innerHTML = "";
  timelineLabels.innerHTML = "";

  for (const seg of segments) {
    const s = summarizeFrame(seg);
    const levelClass = s.congestionLevel ? `level-${s.congestionLevel}` : "level-unknown";

    const block = document.createElement("div");
    block.className = `timeline-block ${levelClass}`;
    block.title = `[${s.timestampLabel}] 사람 ${s.totalPeople} | ${s.congestionLevel || "-"} | ${actionLabel(s.action)}`;
    timelineStrip.appendChild(block);

    const label = document.createElement("div");
    label.className = "timeline-label";
    label.textContent = s.timestampLabel;
    timelineLabels.appendChild(label);
  }
}

// ── 카드 본문 (펼침 영역) HTML 생성 ────────────────────────────
function buildCardBodyHTML(result, error) {
  if (error) {
    return `<p class="card-error-text">${error}</p>`;
  }

  const hotspots = (result.local_hotspots || [])
    .map((h) => `<li>${h}</li>`)
    .join("");

  // tool_raw: 도구(손발 역할)가 준 사실 원본
  const toolRaw = result.tool_raw || null;
  let zoneCounts = "";
  if (toolRaw && toolRaw.zone_counts && Object.keys(toolRaw.zone_counts).length > 0) {
    const rows = Object.entries(toolRaw.zone_counts)
      .map(([zone, count]) => `<tr><td>${zone}</td><td>${count}</td></tr>`)
      .join("");
    zoneCounts = `
      <div class="detail-section">
        <strong>구역별 인원 — 도구(손발 역할) 원본</strong>
        <table class="zone-table">
          <tr><th>구역</th><th>인원</th></tr>
          ${rows}
        </table>
      </div>`;
  }

  const tracks = toolRaw?.tracks || [];
  const tracksHTML = tracks.length
    ? `<details class="tracks-details">
        <summary>Track 목록 (${tracks.length}명)</summary>
        <ul class="track-list">
          ${tracks
            .map((t) => {
              const cx = (t.center || [])[0]?.toFixed(1) ?? "?";
              const cy = (t.center || [])[1]?.toFixed(1) ?? "?";
              return `<li>ID ${t.track_id} — center (${cx}, ${cy})</li>`;
            })
            .join("")}
        </ul>
      </details>`
    : "";

  return `
    <div class="detail-section">
      <strong>Reasoning</strong>
      <p>${result.reasoning || "-"}</p>
    </div>
    ${hotspots ? `<div class="detail-section"><strong>Local Hotspots</strong><ul>${hotspots}</ul></div>` : ""}
    ${zoneCounts}
    ${tracksHTML}
    <div class="detail-meta">
      도구 호출: ${result.tool_called ? "예" : "아니오"}
      &nbsp;|&nbsp; frame_timestamp: ${result.frame_timestamp ?? "-"}s
    </div>
  `;
}

// ── 카드 하나 생성 ──────────────────────────────────────────────
function buildCard(record) {
  const s = summarizeFrame(record);
  const result = record.result || {};
  const levelClass = s.congestionLevel ? `level-${s.congestionLevel}` : "level-unknown";

  const card = document.createElement("div");
  card.className = "frame-card";

  const header = document.createElement("div");
  header.className = "frame-card-header";
  header.innerHTML = `
    <span class="card-timestamp">[${s.timestampLabel}]</span>
    <span class="card-people">사람 ${s.totalPeople}</span>
    <span class="level-badge ${levelClass}">${s.congestionLevel || "-"}</span>
    <span class="card-action">${actionLabel(s.action)}</span>
    <span class="card-dist">${s.distributionShort}</span>
    <span class="card-toggle">▼</span>
  `;

  const body = document.createElement("div");
  body.className = "frame-card-body";
  body.hidden = true;
  body.innerHTML = buildCardBodyHTML(result, record.error);

  header.addEventListener("click", () => {
    const isOpen = !body.hidden;
    body.hidden = isOpen;
    header.querySelector(".card-toggle").textContent = isOpen ? "▼" : "▲";
  });

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

// ── 전체 결과 렌더링 ────────────────────────────────────────────
function renderResults(payload) {
  const segments = payload.segments || [];
  const ok = segments.filter((s) => s.result).length;
  const total = segments.length;

  resultsMeta.textContent =
    `${ok}/${total} 세그먼트 분석 완료` +
    (payload.saved_result ? ` | ${payload.saved_result}` : "");

  buildTimeline(segments);

  frameCards.innerHTML = "";
  for (const seg of segments) {
    frameCards.appendChild(buildCard(seg));
  }

  resultsSection.hidden = false;
}

// ── 비디오 파일 선택 ────────────────────────────────────────────
videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }

  if (!file) {
    preview.removeAttribute("src");
    preview.style.display = "none";
    emptyState.style.display = "grid";
    return;
  }

  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  preview.style.display = "block";
  emptyState.style.display = "none";
  fileInfo.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
});

// ── 분석 폼 제출 ────────────────────────────────────────────────
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!videoInput.files[0]) {
    setStatus("Error", "error");
    return;
  }

  setStatus("Running", "running");
  submitButton.disabled = true;
  submitButton.textContent = "Analyzing…";
  resultsSection.hidden = true;

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Analysis failed.");
    }
    renderResults(payload);
    setStatus("Done", "done");
  } catch (error) {
    setStatus("Error", "error");
    resultsMeta.textContent = error.message;
    resultsSection.hidden = false;
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = '<span class="button-icon">▶</span>Analyze';
  }
});
