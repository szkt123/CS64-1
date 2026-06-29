const DIMENSIONS = [
  { key: "clarity", label: "Clarity" },
  { key: "relevance", label: "Relevance" },
  { key: "informativeness", label: "Informativeness" },
  { key: "structure", label: "Structure" }
];

let records = [];
let annotations = {};
let currentIndex = 0;
const MAX_VISIBLE_IMAGES = 2;

const annotatorInput = document.getElementById("annotatorInput");
const figuresFile = document.getElementById("figuresFile");
const importFile = document.getElementById("importFile");
const imageBaseInput = document.getElementById("imageBaseInput");

const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const saveBtn = document.getElementById("saveBtn");
const clearBtn = document.getElementById("clearBtn");
const exportBtn = document.getElementById("exportBtn");
const reloadImageBtn = document.getElementById("reloadImageBtn");
const addEvidenceBtn = document.getElementById("addEvidenceBtn");

const statusText = document.getElementById("statusText");
const totalCount = document.getElementById("totalCount");
const savedCount = document.getElementById("savedCount");
const currentPosition = document.getElementById("currentPosition");
const sampleMeta = document.getElementById("sampleMeta");

const figureImage = document.getElementById("figureImage");
const captionText = document.getElementById("captionText");
const paragraphsText = document.getElementById("paragraphsText");
const nearbyText = document.getElementById("nearbyText");

const scoreSection = document.getElementById("scoreSection");
const evidenceList = document.getElementById("evidenceList");

const dimensionTemplate = document.getElementById("dimensionTemplate");
const evidenceTemplate = document.getElementById("evidenceTemplate");

function makeRecordKey(record) {
  return `${record.paper_id}__${record.figure_id}`;
}

function parseJsonl(text) {
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => JSON.parse(line));
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatTextBlock(value) {
  if (Array.isArray(value)) {
    if (!value.length) return "<em>None</em>";
    return value.map(v => `<p>${escapeHtml(v)}</p>`).join("");
  }
  if (!value) return "<em>None</em>";
  return `<p>${escapeHtml(value)}</p>`;
}

function getImageSrc(record) {
  const base = imageBaseInput.value.trim();
  let rawPath = record.figure_image_path || "";

  // If already a URL (http/https/file), use as-is
  if (/^(https?|file):\/\//i.test(rawPath)) return rawPath;

  // Fix known path mismatch: /Volumes/JHAO/data/ -> /Volumes/JHAO/data_v1/
  rawPath = rawPath.replace("/Volumes/JHAO/data/", "/Volumes/JHAO/data_v1/");

  let fullPath;
  if (!base || rawPath.startsWith("/")) {
    // rawPath is already absolute — ignore base to avoid double-path
    fullPath = rawPath;
  } else {
    // rawPath is relative — join with base
    fullPath = base.replace(/\/$/, "") + "/" + rawPath.replace(/^\//, "");
  }

  // Convert absolute filesystem paths to file:// URLs so the browser can load them
  if (fullPath.startsWith("/")) {
    return "file://" + fullPath;
  }
  return fullPath;
}


async function autoLoadDefaultBatch() {
  try {
    const response = await fetch("./batch_1.jsonl");
    if (!response.ok) return;
    const text = await response.text();
    records = parseJsonl(text).slice(0, MAX_VISIBLE_IMAGES);
    currentIndex = 0;
    annotations = {};
    imageBaseInput.value = "./";
    statusText.textContent = `Batch 1 auto-loaded: ${records.length} samples (first two images only)`;
    renderRecord();
  } catch (err) {
    console.warn("Auto load batch_1.jsonl failed", err);
  }
}

function buildDefaultAnnotation(record) {
  return {
    paper_id: record.paper_id,
    paper_title: record.paper_title || "",
    figure_id: record.figure_id,
    figure_image_path: record.figure_image_path || "",
    figure_type: record.figure_type || "",
    caption_text: record.caption_text || "",
    citing_paragraphs: Array.isArray(record.citing_paragraphs) ? [...record.citing_paragraphs] : [],
    section_title: record.section_title || "",
    nearby_context: Array.isArray(record.nearby_context) ? [...record.nearby_context] : [],
    annotator_id: annotatorInput.value.trim(),
    is_deleted: false,
    scores: {
      clarity: { score: null, rationale: "" },
      relevance: { score: null, rationale: "" },
      informativeness: { score: null, rationale: "" },
      structure: { score: null, rationale: "" }
    },
    evidence: []
  };
}

function getCurrentRecord() {
  return records[currentIndex] || null;
}

function getCurrentAnnotation() {
  const record = getCurrentRecord();
  if (!record) return null;
  const key = makeRecordKey(record);
  if (!annotations[key]) {
    annotations[key] = buildDefaultAnnotation(record);
  }
  return annotations[key];
}

function updateCounters() {
  totalCount.textContent = records.length;
  savedCount.textContent = Object.keys(annotations).length;
  currentPosition.textContent = records.length ? `${currentIndex + 1} / ${records.length}` : "0 / 0";
}

function renderScoreSection(annotation) {
  scoreSection.innerHTML = "";

  DIMENSIONS.forEach(dim => {
    const node = dimensionTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".dimension-title").textContent = dim.label;

    const scoreGroup = node.querySelector(".score-group");
    for (let i = 1; i <= 5; i++) {
      const label = document.createElement("label");
      label.style.marginRight = "10px";

      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `score_${dim.key}`;
      radio.value = String(i);
      radio.checked = annotation.scores?.[dim.key]?.score === i;

      label.appendChild(radio);
      label.append(` ${i}`);
      scoreGroup.appendChild(label);
    }

    const rationaleInput = node.querySelector(".rationale-input");
    rationaleInput.dataset.dimension = dim.key;
    rationaleInput.value = annotation.scores?.[dim.key]?.rationale || "";

    scoreSection.appendChild(node);
  });
}

function renderEvidenceList(annotation) {
  evidenceList.innerHTML = "";

  const evidenceArr = Array.isArray(annotation.evidence) ? annotation.evidence : [];

  evidenceArr.forEach((ev, idx) => {
    const node = evidenceTemplate.content.firstElementChild.cloneNode(true);

    const sourceSelect = node.querySelector(".evidence-source");
    const textArea = node.querySelector(".evidence-text");
    const removeBtn = node.querySelector(".remove-evidence-btn");

    sourceSelect.value = ev.source || "caption";
    textArea.value = ev.text || "";

    sourceSelect.addEventListener("change", () => {
      annotation.evidence[idx].source = sourceSelect.value;
    });

    textArea.addEventListener("input", () => {
      annotation.evidence[idx].text = textArea.value;
    });

    removeBtn.addEventListener("click", () => {
      annotation.evidence.splice(idx, 1);
      renderEvidenceList(annotation);
    });

    evidenceList.appendChild(node);
  });
}

function renderSampleMeta(record, annotation) {
  sampleMeta.textContent = JSON.stringify(
    {
      paper_id: record.paper_id,
      paper_title: record.paper_title,
      figure_id: record.figure_id,
      figure_type: record.figure_type,
      figure_image_path: record.figure_image_path,
      is_deleted: annotation.is_deleted
    },
    null,
    2
  );
}

function renderRecord() {
  const record = getCurrentRecord();
  if (!record) {
    figureImage.removeAttribute("src");
    captionText.innerHTML = "<em>No data loaded</em>";
    paragraphsText.innerHTML = "<em>No data loaded</em>";
    nearbyText.innerHTML = "<em>No data loaded</em>";
    sampleMeta.textContent = "";
    statusText.textContent = "No data loaded";
    updateCounters();
    return;
  }

  const annotation = getCurrentAnnotation();

  figureImage.src = getImageSrc(record);
  figureImage.alt = `${record.paper_id} - ${record.figure_id}`;

  captionText.innerHTML = formatTextBlock(record.caption_text);
  paragraphsText.innerHTML = formatTextBlock(record.citing_paragraphs);
  nearbyText.innerHTML = formatTextBlock(record.nearby_context);

  renderScoreSection(annotation);
  renderEvidenceList(annotation);
  renderSampleMeta(record, annotation);
  updateCounters();

  statusText.textContent = annotation.is_deleted
    ? "The current sample is marked as deleted and will be excluded from export."
    : "Sample loaded.";
}

function saveCurrent() {
  const record = getCurrentRecord();
  if (!record) return;

  const annotation = getCurrentAnnotation();
  annotation.annotator_id = annotatorInput.value.trim();

  DIMENSIONS.forEach(dim => {
    const checked = document.querySelector(`input[name="score_${dim.key}"]:checked`);
    const rationale = document.querySelector(`.rationale-input[data-dimension="${dim.key}"]`);

    annotation.scores[dim.key] = {
      score: checked ? Number(checked.value) : null,
      rationale: rationale ? rationale.value.trim() : ""
    };
  });
}

function clearCurrent() {
  const annotation = getCurrentAnnotation();
  if (!annotation) return;

  annotation.is_deleted = false;
  annotation.evidence = [];
  DIMENSIONS.forEach(dim => {
    annotation.scores[dim.key] = { score: null, rationale: "" };
  });

  renderRecord();
}

function exportJsonl() {
  saveCurrent();

  const exported = records
    .map(record => {
      const key = makeRecordKey(record);
      return annotations[key] || buildDefaultAnnotation(record);
    })
    .filter(item => !item.is_deleted);

  const content = exported.map(item => JSON.stringify(item)).join("\n");
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "filtered_annotations.jsonl";
  a.click();

  URL.revokeObjectURL(url);
}

figuresFile.addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;

  const text = await file.text();
  try {
    records = parseJsonl(text).slice(0, MAX_VISIBLE_IMAGES);
    annotations = {};
    currentIndex = 0;
    statusText.textContent = `Loaded ${records.length} records (first two images only).`;
    renderRecord();
  } catch (err) {
    console.error(err);
    statusText.textContent = "Load failed. Please check the JSONL format.";
  }
});

importFile.addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;

  const text = await file.text();
  try {
    const rows = parseJsonl(text);
    rows.forEach(row => {
      const key = `${row.paper_id}__${row.figure_id}`;
      annotations[key] = row;
    });
    statusText.textContent = `Imported ${rows.length} existing annotations.`;
    renderRecord();
  } catch (err) {
    console.error(err);
    statusText.textContent = "Annotation import failed. Please check the JSONL format.";
  }
});

prevBtn.addEventListener("click", () => {
  if (!records.length) return;
  saveCurrent();
  if (currentIndex > 0) {
    currentIndex -= 1;
    renderRecord();
  }
});

nextBtn.addEventListener("click", () => {
  if (!records.length) return;
  saveCurrent();
  if (currentIndex < records.length - 1) {
    currentIndex += 1;
    renderRecord();
  }
});

saveBtn.addEventListener("click", () => {
  saveCurrent();
  statusText.textContent = "Current sample saved.";
  updateCounters();
});

clearBtn.addEventListener("click", () => {
  clearCurrent();
  statusText.textContent = "Current sample cleared.";
});

exportBtn.addEventListener("click", exportJsonl);

reloadImageBtn.addEventListener("click", () => {
  const record = getCurrentRecord();
  if (!record) return;
  figureImage.src = "";
  setTimeout(() => {
    figureImage.src = getImageSrc(record);
  }, 50);
});

addEvidenceBtn.addEventListener("click", () => {
  const annotation = getCurrentAnnotation();
  if (!annotation) return;
  annotation.evidence.push({ source: "caption", text: "" });
  renderEvidenceList(annotation);
});

imageBaseInput.addEventListener("input", () => {
  const record = getCurrentRecord();
  if (!record) return;
  figureImage.src = getImageSrc(record);
});

figureImage.addEventListener("error", () => {
  statusText.textContent = `Image failed to load: ${getCurrentRecord()?.figure_image_path || ""}`;
});

figureImage.addEventListener("load", () => {
  const annotation = getCurrentAnnotation();
  if (!annotation) return;
  statusText.textContent = annotation.is_deleted
    ? "The current sample is marked as deleted and will be excluded from export."
    : "Image loaded successfully.";
});

document.addEventListener("keydown", e => {
  if (!records.length) return;

  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;

  if (e.key === "ArrowLeft") prevBtn.click();
  if (e.key === "ArrowRight") nextBtn.click();
});

// Delete / restore controls
const deleteBtn = document.createElement("button");
deleteBtn.textContent = "Delete This Image";
deleteBtn.type = "button";
deleteBtn.className = "ghost";

const restoreBtn = document.createElement("button");
restoreBtn.textContent = "Restore This Image";
restoreBtn.type = "button";
restoreBtn.className = "ghost";

document.querySelector(".controls-grid").appendChild(deleteBtn);
document.querySelector(".controls-grid").appendChild(restoreBtn);

deleteBtn.addEventListener("click", () => {
  const annotation = getCurrentAnnotation();
  if (!annotation) return;
  annotation.is_deleted = true;
  renderRecord();
});

restoreBtn.addEventListener("click", () => {
  const annotation = getCurrentAnnotation();
  if (!annotation) return;
  annotation.is_deleted = false;
  renderRecord();
});

renderRecord();

autoLoadDefaultBatch();
