const form = document.querySelector("#analysisForm");
const videoInput = document.querySelector("#videoInput");
const preview = document.querySelector("#preview");
const emptyState = document.querySelector("#emptyState");
const submitButton = document.querySelector("#submitButton");
const statusBadge = document.querySelector("#statusBadge");
const peopleValue = document.querySelector("#peopleValue");
const levelValue = document.querySelector("#levelValue");
const actionValue = document.querySelector("#actionValue");
const distributionValue = document.querySelector("#distributionValue");
const reasoningValue = document.querySelector("#reasoningValue");
const fileInfo = document.querySelector("#fileInfo");

let previewUrl = null;

function setStatus(text, className) {
  statusBadge.textContent = text;
  statusBadge.className = `status-badge ${className}`;
}

function renderResult(payload) {
  const result = payload.segments?.[0]?.result || {};
  peopleValue.textContent = result.total_people ?? "-";
  levelValue.textContent = result.congestion_level ?? "-";
  actionValue.textContent = result.action ?? "-";
  distributionValue.textContent = result.distribution_summary ?? "-";
  reasoningValue.textContent = result.reasoning ?? "-";
  fileInfo.textContent = `result: ${payload.saved_result} / upload: ${payload.uploaded_video}`;
}

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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!videoInput.files[0]) {
    setStatus("Error", "error");
    reasoningValue.textContent = "Select a video first.";
    return;
  }

  setStatus("Running", "running");
  submitButton.disabled = true;
  submitButton.textContent = "Analyzing";
  reasoningValue.textContent = "The LLM is deciding whether to call tools.";

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Analysis failed.");
    }
    renderResult(payload);
    setStatus("Done", "done");
  } catch (error) {
    setStatus("Error", "error");
    reasoningValue.textContent = error.message;
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = '<span class="button-icon">▶</span>Analyze';
  }
});
