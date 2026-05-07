const state = {
  snapshot: null,
  analysis: null,
  research: null,
  defaults: [],
  selectedProject: null,
  selectedSignal: null,
};

const elements = {
  projectSelect: document.getElementById("projectSelect"),
  refreshButton: document.getElementById("refreshButton"),
  toggleAdminButton: document.getElementById("toggleAdminButton"),
  adminPanel: document.getElementById("adminPanel"),
  metricGrid: document.getElementById("metricGrid"),
  timelineChart: document.getElementById("timelineChart"),
  compareBars: document.getElementById("compareBars"),
  sourceStatusList: document.getElementById("sourceStatusList"),
  regionList: document.getElementById("regionList"),
  signalGrid: document.getElementById("signalGrid"),
  explainTitle: document.getElementById("explainTitle"),
  explainSummary: document.getElementById("explainSummary"),
  explainMeta: document.getElementById("explainMeta"),
  explainLinks: document.getElementById("explainLinks"),
  itemList: document.getElementById("itemList"),
  sourceCatalog: document.getElementById("sourceCatalog"),
  differentiatorList: document.getElementById("differentiatorList"),
  strategyRule: document.getElementById("strategyRule"),
  projectName: document.getElementById("projectName"),
  projectDescription: document.getElementById("projectDescription"),
  latencyProfile: document.getElementById("latencyProfile"),
  lastSweep: document.getElementById("lastSweep"),
  laneStrip: document.getElementById("laneStrip"),
  projectForm: document.getElementById("projectForm"),
  projectNameInput: document.getElementById("projectNameInput"),
  projectDescriptionInput: document.getElementById("projectDescriptionInput"),
  projectKeywordsInput: document.getElementById("projectKeywordsInput"),
  projectLatencyInput: document.getElementById("projectLatencyInput"),
  projectSearchInput: document.getElementById("projectSearchInput"),
  projectGallery: document.getElementById("projectGallery"),
  launchCustomProjectButton: document.getElementById("launchCustomProjectButton"),
  sourceCheckboxes: document.getElementById("sourceCheckboxes"),
  officialOnlyInput: document.getElementById("officialOnlyInput"),
  loadDefaultProjectButton: document.getElementById("loadDefaultProjectButton"),
  searchInput: document.getElementById("searchInput"),
  sourceFilter: document.getElementById("sourceFilter"),
};

async function requestJson(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function cleanDisplayText(value) {
  return String(value ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/\\([\\`*_{}\[\]()#+\-.!>~|])/g, "$1")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, "$1")
    .replace(/^\s*\|?(?:\s*:?-+:?\s*\|)+\s*$/gm, " ")
    .replace(/^\s*[-*_]{3,}\s*$/gm, " ")
    .replace(/^\s{0,3}(?:#{1,6}|>+)\s*/gm, "")
    .replace(/^\s{0,3}(?:[-*+]|\d+\.)\s+/gm, "")
    .replace(/\|/g, " ")
    .replace(/\*\*|__|~~|`+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeExternalUrl(value) {
  try {
    const url = new URL(String(value ?? ""), window.location.origin);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : "#";
  } catch {
    return "#";
  }
}

function formatExternalLabel(value, fallback = "Open evidence") {
  const safeUrl = safeExternalUrl(value);
  if (safeUrl === "#") {
    return fallback;
  }
  try {
    const parsed = new URL(safeUrl);
    const host = parsed.hostname.replace(/^www\./, "");
    if (host.includes("youtube.com")) {
      return "Watch on YouTube";
    }
    if (host.includes("t.me")) {
      return "Open Telegram post";
    }
    if (host.includes("reddit.com")) {
      return "Open Reddit thread";
    }
    if (host.includes("news.google.com")) {
      return "Open Google News search";
    }
    if (host.includes("data.gov.in")) {
      return "Open data.gov.in source";
    }
    if (host.includes("cdsco.gov.in")) {
      return "Open CDSCO source";
    }
    if (host.includes("nhm.gov.in")) {
      return "Open NHM source";
    }
    return `Open ${host}`;
  } catch {
    return fallback;
  }
}

function splitKeywords(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getSelectedSources() {
  return [...elements.sourceCheckboxes.querySelectorAll("input:checked")].map(
    (input) => input.value,
  );
}

function getMvpSourceNames() {
  return (state.research?.source_catalog ?? [])
    .filter((source) => source.mvp)
    .map((source) => source.name);
}

function getDefaultProjectIndex(project) {
  if (!project) {
    return -1;
  }
  return state.defaults.findIndex((entry) => entry.name === project.name);
}

function titleCaseWords(value) {
  return String(value ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function buildCustomProjectFromQuery(query) {
  const cleaned = String(query ?? "").trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return null;
  }

  const keywordParts = cleaned
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((part) => part.length > 2);
  const keywords = [...new Set([cleaned.toLowerCase(), ...keywordParts])].slice(0, 8);

  return {
    name: `${titleCaseWords(cleaned)} watch`,
    description: `Track live evidence for ${cleaned} across patient chatter, expert explainers, public broadcasts, and Indian official context.`,
    keywords,
    sources: getMvpSourceNames(),
    latency_profile: "Realtime",
    include_official_only: false,
  };
}

async function activateProject(project) {
  state.selectedProject = project;
  hydrateForm(project);
  window.localStorage.setItem("swasthyaSignals.project", JSON.stringify(state.selectedProject));
  renderProjectOptions();
  renderProjectLibrary();
  await analyzeSelectedProject(false);
}

function renderProjectOptions() {
  elements.projectSelect.innerHTML = "";
  state.defaults.forEach((project, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = project.name;
    elements.projectSelect.append(option);
  });

  const selectedIndex = getDefaultProjectIndex(state.selectedProject);
  if (selectedIndex === -1 && state.selectedProject) {
    const customOption = document.createElement("option");
    customOption.value = "custom";
    customOption.textContent = `${state.selectedProject.name} (custom)`;
    elements.projectSelect.append(customOption);
  }
  elements.projectSelect.value = selectedIndex >= 0 ? String(selectedIndex) : "custom";
}

function renderSourceCheckboxes() {
  const catalog = state.research?.source_catalog ?? [];
  elements.sourceCheckboxes.innerHTML = "";
  catalog.forEach((source) => {
    const label = document.createElement("label");
    label.className = "checkbox-row";
    label.innerHTML = `
      <input type="checkbox" value="${source.name}" ${source.mvp ? "checked" : ""}>
      <span>${source.label}</span>
    `;
    elements.sourceCheckboxes.append(label);
  });
}

function updateProjectBrief(project) {
  elements.projectName.textContent = project.name;
  elements.projectDescription.textContent = project.description;
  elements.latencyProfile.textContent = project.latency_profile;
}

function renderSnapshotMeta() {
  const generatedAt = state.snapshot?.generated_at;
  elements.lastSweep.textContent = generatedAt ? formatTimestamp(generatedAt) : "Awaiting refresh";
}

function renderLaneStrip() {
  const statuses = state.snapshot?.source_status ?? [];
  const laneDefinitions = [
    {
      key: "social",
      label: "Patient chatter",
      sources: ["reddit"],
      detail: "Patient and caregiver narratives before formal escalation",
    },
    {
      key: "video",
      label: "Video explainers",
      sources: ["youtube"],
      detail: "Expert and public-health channels that add fast visual context",
    },
    {
      key: "broadcast",
      label: "Public broadcasts",
      sources: ["telegram"],
      detail: "Government and mission channels that push notices before formal reports",
    },
    {
      key: "validation",
      label: "Open-web validation",
      sources: ["google_news"],
      detail: "Rapid corroboration from public news coverage",
    },
    {
      key: "official",
      label: "Official + baseline",
      sources: ["cdsco", "nhm", "data_gov"],
      detail: "Regulation, mission guidance, and open datasets in one lane",
    },
  ];

  elements.laneStrip.innerHTML = laneDefinitions
    .map((lane) => {
      const matches = statuses.filter((status) => lane.sources.includes(status.name));
      const itemCount = matches.reduce((sum, status) => sum + status.item_count, 0);
      const okCount = matches.filter((status) => status.ok).length;
      const quality = okCount === matches.length && itemCount > 0 ? "Live" : itemCount > 0 ? "Partial" : "Waiting";
      return `
        <article class="lane-card panel">
          <p class="eyebrow">${lane.label}</p>
          <strong>${itemCount}</strong>
          <span>${quality}</span>
          <p>${lane.detail}</p>
        </article>
      `;
    })
    .join("");
}

function renderProjectLibrary() {
  const query = elements.projectSearchInput.value.trim().toLowerCase();
  const visibleProjects = state.defaults.filter((project) => {
    if (!query) {
      return true;
    }
    const merged = `${project.name} ${project.description} ${(project.keywords ?? []).join(" ")}`.toLowerCase();
    return merged.includes(query);
  });
  const customProject = buildCustomProjectFromQuery(elements.projectSearchInput.value);

  if (!visibleProjects.length && !customProject) {
    elements.projectGallery.innerHTML = '<div class="empty-state">No projects match the current search.</div>';
    return;
  }

  const cards = [];
  if (customProject) {
    const activeClass = state.selectedProject?.name === customProject.name ? "active" : "";
    cards.push(`
      <article class="project-card project-card-custom ${activeClass}">
        <div class="catalog-meta">
          <span>Custom</span>
          <span>${customProject.sources.length} sources</span>
        </div>
        <h3>${escapeHtml(customProject.name)}</h3>
        <p>${escapeHtml(customProject.description)}</p>
        <div class="chip-row">
          ${customProject.keywords.map((keyword) => `<span class="chip alt">${escapeHtml(keyword)}</span>`).join("")}
        </div>
        <div class="project-card-footer">
          <span>Built from what the user typed</span>
          <button class="action-button primary small-button" type="button" data-project-kind="custom">Launch issue</button>
        </div>
      </article>
    `);
  }

  cards.push(
    ...visibleProjects.map((project, index) => {
      const activeClass = state.selectedProject?.name === project.name ? "active" : "";
      const safeName = escapeHtml(project.name);
      const safeDescription = escapeHtml(project.description);
      const keywords = (project.keywords ?? [])
        .slice(0, 6)
        .map((keyword) => `<span class="chip">${escapeHtml(keyword)}</span>`)
        .join("");
      return `
        <article class="project-card ${activeClass}">
          <div class="catalog-meta">
            <span>${escapeHtml(project.latency_profile ?? "Realtime")}</span>
            <span>${(project.sources ?? []).length} sources</span>
          </div>
          <h3>${safeName}</h3>
          <p>${safeDescription}</p>
          <div class="chip-row">${keywords}</div>
          <div class="project-card-footer">
            <span>${project.include_official_only ? "Official only" : "Open web + official"}</span>
            <button class="action-button secondary small-button" type="button" data-project-index="${index}">Load project</button>
          </div>
        </article>
      `;
    }),
  );

  elements.projectGallery.innerHTML = cards.join("");

  [...elements.projectGallery.querySelectorAll("[data-project-index]")].forEach((button) => {
    button.addEventListener("click", async () => {
      const project = state.defaults[Number(button.dataset.projectIndex)];
      await activateProject(project);
    });
  });

  [...elements.projectGallery.querySelectorAll("[data-project-kind='custom']")].forEach((button) => {
    button.addEventListener("click", async () => {
      const project = buildCustomProjectFromQuery(elements.projectSearchInput.value);
      if (project) {
        await activateProject(project);
      }
    });
  });
}

function renderMetrics() {
  const metrics = state.analysis?.metrics;
  if (!metrics) {
    return;
  }
  const cards = [
    ["Evidence items", metrics.item_count, "Live records matching the project brief"],
    ["Signals", metrics.signal_count, "Explainable alerts ready for review"],
    ["India-coded", metrics.india_count, "Items mapped to India or Indian official context"],
    ["Global-coded", metrics.global_count, "Cross-border comparison evidence"],
    ["Official references", metrics.official_count, "Regulatory and public-health anchors"],
  ];
  elements.metricGrid.innerHTML = cards
    .map(
      ([title, value, subtitle]) => `
        <article class="metric-card panel">
          <h3>${title}</h3>
          <strong>${value}</strong>
          <span>${subtitle}</span>
        </article>
      `,
    )
    .join("");
}

function renderTimeline() {
  const timeline = state.analysis?.timeline ?? [];
  if (!timeline.length) {
    elements.timelineChart.innerHTML = '<div class="empty-state">No time-series data yet for this brief.</div>';
    return;
  }
  const maxCount = Math.max(...timeline.map((point) => point.count), 1);
  elements.timelineChart.innerHTML = timeline
    .map((point) => {
      const height = Math.max(10, Math.round((point.count / maxCount) * 190));
      return `
        <div class="timeline-bar">
          <strong>${point.count}</strong>
          <div class="timeline-bar-fill" style="height:${height}px"></div>
          <span>${point.day === "unknown" ? "Unknown" : point.day.slice(5)}</span>
        </div>
      `;
    })
    .join("");
}

function renderComparison() {
  const metrics = state.analysis?.metrics;
  const sourceStatus = state.snapshot?.source_status ?? [];
  const regions = state.analysis?.region_breakdown ?? [];
  if (!metrics) {
    return;
  }

  const indiaMax = Math.max(metrics.india_count, metrics.global_count, 1);
  elements.compareBars.innerHTML = [
    ["India", metrics.india_count],
    ["Rest of world", metrics.global_count],
  ]
    .map(
      ([label, value]) => `
        <div class="compare-card">
          <span>${label}</span>
          <strong>${value}</strong>
          <div class="compare-track">
            <div class="compare-fill" style="width:${Math.max(8, (value / indiaMax) * 100)}%"></div>
          </div>
        </div>
      `,
    )
    .join("");

  elements.sourceStatusList.innerHTML = sourceStatus
    .map((status) => {
      const statusClass = status.ok && status.item_count > 0 ? "status-ok" : "status-empty";
      const suffix = status.item_count > 0 ? `${status.item_count} items` : "No items yet";
      return `
        <div class="status-row">
          <span>${status.label}</span>
          <span class="${statusClass}">${suffix}</span>
        </div>
      `;
    })
    .join("");

  elements.regionList.innerHTML = regions.length
    ? regions
        .slice(0, 6)
        .map(
          (region) => `
            <div class="mini-list-row">
              <span>${region.region}</span>
              <span>${region.count}</span>
            </div>
          `,
        )
        .join("")
    : '<div class="empty-state">No region breakdown available.</div>';
}

function renderSignals() {
  const signals = state.analysis?.signals ?? [];
  if (!signals.length) {
    elements.signalGrid.innerHTML = '<div class="empty-state">No signals fired for the current keywords. Widen the brief or refresh live data.</div>';
    renderSignalDetail(null);
    return;
  }

  if (!state.selectedSignal || !signals.find((signal) => signal.title === state.selectedSignal.title)) {
    state.selectedSignal = signals[0];
  }

  elements.signalGrid.innerHTML = signals
    .map((signal) => {
      const activeClass = state.selectedSignal?.title === signal.title ? "active" : "";
      const tags = signal.tags.length
        ? signal.tags.map((tag) => `<span class="chip alt">${tag}</span>`).join("")
        : '<span class="chip">Unclassified</span>';
      return `
        <article class="signal-card ${activeClass}" data-signal-title="${escapeHtml(signal.title)}">
          <div class="chip-row">
            <span class="chip">${signal.region}</span>
            ${tags}
          </div>
          <h3>${signal.title}</h3>
          <p>${signal.summary}</p>
          <div class="signal-footer">
            <span>${signal.evidence_count} evidence items</span>
            <span class="confidence">${signal.confidence}/100</span>
          </div>
        </article>
      `;
    })
    .join("");

  [...elements.signalGrid.querySelectorAll(".signal-card")].forEach((card) => {
    card.addEventListener("click", () => {
      const signal = signals.find((entry) => entry.title === card.dataset.signalTitle);
      state.selectedSignal = signal;
      renderSignals();
      renderSignalDetail(signal);
    });
  });

  renderSignalDetail(state.selectedSignal);
}

function renderSignalDetail(signal) {
  if (!signal) {
    elements.explainTitle.textContent = "Select a signal";
    elements.explainSummary.textContent = "Evidence details, source overlap, and official references will appear here.";
    elements.explainMeta.innerHTML = "";
    elements.explainLinks.innerHTML = "";
    return;
  }

  elements.explainTitle.textContent = signal.title;
  elements.explainSummary.textContent = signal.summary;
  elements.explainMeta.innerHTML = `
    <span class="chip">Confidence ${signal.confidence}/100</span>
    <span class="chip alt">${signal.evidence_count} evidence items</span>
    ${signal.sources.map((source) => `<span class="chip">${source}</span>`).join("")}
  `;

  const links = [...signal.official_references, ...signal.example_urls].slice(0, 6);
  elements.explainLinks.innerHTML = links.length
    ? links
        .map((url) => {
          const resolvedUrl = safeExternalUrl(url);
          const safeUrl = escapeHtml(resolvedUrl);
          const label = escapeHtml(formatExternalLabel(url));
          const compactUrl = escapeHtml(resolvedUrl.replace(/^https?:\/\//, ""));
          return `
            <a class="evidence-link" href="${safeUrl}" target="_blank" rel="noreferrer">
              <strong>${label}</strong>
              <span>${compactUrl}</span>
            </a>
          `;
        })
        .join("")
    : '<div class="empty-state">No evidence links available for this signal.</div>';
}

function populateSourceFilter() {
  const breakdown = state.analysis?.source_breakdown ?? [];
  const currentValue = elements.sourceFilter.value || "all";
  elements.sourceFilter.innerHTML = '<option value="all">All sources</option>';
  breakdown.forEach((entry) => {
    const option = document.createElement("option");
    option.value = entry.source;
    option.textContent = `${entry.source} (${entry.count})`;
    elements.sourceFilter.append(option);
  });
  elements.sourceFilter.value = breakdown.some((entry) => entry.source === currentValue)
    ? currentValue
    : "all";
}

function renderExplorer() {
  const items = state.analysis?.items ?? [];
  const query = elements.searchInput.value.trim().toLowerCase();
  const sourceFilter = elements.sourceFilter.value;
  const filtered = items.filter((item) => {
    const merged = `${cleanDisplayText(item.title)} ${cleanDisplayText(item.body)}`.toLowerCase();
    const matchesQuery = !query || merged.includes(query);
    const matchesSource = sourceFilter === "all" || item.source === sourceFilter;
    return matchesQuery && matchesSource;
  });

  if (!filtered.length) {
    elements.itemList.innerHTML = '<div class="empty-state">No evidence items match the current filters.</div>';
    return;
  }

  elements.itemList.innerHTML = filtered
    .map((item) => {
      const safeTitle = escapeHtml(cleanDisplayText(item.title));
      const safeBody = escapeHtml(cleanDisplayText(item.body || "No body text available."));
      const safeSourceLabel = escapeHtml(item.source_label);
      const safeRegion = escapeHtml(item.region);
      const safeSentiment = escapeHtml(item.sentiment);
      const safeUrl = escapeHtml(safeExternalUrl(item.url));
      const linkLabel = escapeHtml(formatExternalLabel(item.url));
      const chips = Object.values(item.entities)
        .flat()
        .slice(0, 6)
        .map((value) => `<span class="chip">${escapeHtml(value)}</span>`)
        .join("");
      return `
        <article class="item-card">
          <div class="item-meta">
            <span>${safeSourceLabel}</span>
            <span>${safeRegion}</span>
            <span>${safeSentiment}</span>
            <span>${item.official ? "official" : "social"}</span>
          </div>
          <h3>${safeTitle}</h3>
          <p>${safeBody}</p>
          <div class="chip-row">${chips || '<span class="chip alt">No matched entities</span>'}</div>
          <p><a href="${safeUrl}" target="_blank" rel="noreferrer">${linkLabel}</a></p>
        </article>
      `;
    })
    .join("");
}

function renderResearch() {
  const catalog = state.research?.source_catalog ?? [];
  elements.sourceCatalog.innerHTML = catalog
    .map((source) => {
      const primaryUrl = safeExternalUrl(source.resource_url);
      const primaryLink = primaryUrl !== "#"
        ? `
          <a class="catalog-primary-link" href="${escapeHtml(primaryUrl)}" target="_blank" rel="noreferrer">
            ${escapeHtml(formatExternalLabel(primaryUrl, "Open source homepage"))}
          </a>
        `
        : "";
      const trackedLinks = (source.resource_links ?? [])
        .slice(0, 6)
        .map((resource) => {
          const safeUrl = escapeHtml(safeExternalUrl(resource.url));
          const label = escapeHtml(resource.label);
          return `<a class="resource-chip" href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>`;
        })
        .join("");
      return `
        <article class="catalog-card">
          <div class="catalog-meta">
            <span>${source.mvp ? "MVP" : "Stretch"}</span>
            <span>${source.credentials}</span>
          </div>
          <h3>${source.label}</h3>
          <p><strong>Method:</strong> ${source.method}</p>
          <p><strong>Best for:</strong> ${source.best_for}</p>
          <p><strong>Risk:</strong> ${source.risk}</p>
          <div class="catalog-links">
            ${primaryLink}
            ${trackedLinks ? `<div class="resource-chip-row">${trackedLinks}</div>` : ""}
          </div>
        </article>
      `;
    })
    .join("");

  elements.differentiatorList.innerHTML = (state.research?.differentiators ?? [])
    .map(
      (text, index) => `
        <article class="differentiator-card">
          <p class="eyebrow">Edge ${index + 1}</p>
          <p>${text}</p>
        </article>
      `,
    )
    .join("");

  elements.strategyRule.textContent = state.research?.mvp_strategy?.guiding_rule ?? "";
}

function hydrateForm(project) {
  elements.projectNameInput.value = project.name ?? "";
  elements.projectDescriptionInput.value = project.description ?? "";
  elements.projectKeywordsInput.value = (project.keywords ?? []).join(", ");
  elements.projectLatencyInput.value = project.latency_profile ?? "Realtime";
  elements.officialOnlyInput.checked = Boolean(project.include_official_only);

  [...elements.sourceCheckboxes.querySelectorAll("input")].forEach((input) => {
    input.checked = (project.sources ?? []).includes(input.value);
  });
}

function renderAll() {
  renderProjectOptions();
  renderProjectLibrary();
  renderSnapshotMeta();
  renderLaneStrip();
  renderMetrics();
  renderTimeline();
  renderComparison();
  renderSignals();
  populateSourceFilter();
  renderExplorer();
  renderResearch();
  updateProjectBrief(state.selectedProject);
}

async function refreshSnapshot() {
  state.snapshot = await requestJson("/api/v1/snapshot?refresh=true");
}

async function analyzeSelectedProject(refresh = false) {
  state.analysis = await requestJson(`/api/v1/projects/analyze${refresh ? "?refresh=true" : ""}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.selectedProject),
  });
  renderAll();
}

async function initialize() {
  try {
    const [defaultsPayload, researchPayload] = await Promise.all([
      requestJson("/api/v1/projects/defaults"),
      requestJson("/api/v1/research"),
    ]);
    state.defaults = defaultsPayload.projects;
    state.research = researchPayload;
    renderProjectOptions();
    renderProjectLibrary();
    renderSourceCheckboxes();

    const savedProject = window.localStorage.getItem("swasthyaSignals.project");
    state.selectedProject = savedProject
      ? JSON.parse(savedProject)
      : state.defaults[0];

    hydrateForm(state.selectedProject);
    await refreshSnapshot();
    await analyzeSelectedProject(false);
  } catch (error) {
    elements.metricGrid.innerHTML = `<div class="empty-state">Unable to load the dashboard: ${error.message}</div>`;
  }
}

elements.projectSelect.addEventListener("change", async (event) => {
  if (event.target.value === "custom") {
    return;
  }
  await activateProject(state.defaults[Number(event.target.value)]);
});

elements.refreshButton.addEventListener("click", async () => {
  elements.refreshButton.disabled = true;
  elements.refreshButton.textContent = "Refreshing…";
  await refreshSnapshot();
  await analyzeSelectedProject(false);
  elements.refreshButton.disabled = false;
  elements.refreshButton.textContent = "Refresh live radar";
});

elements.toggleAdminButton.addEventListener("click", () => {
  elements.adminPanel.classList.toggle("hidden");
});

elements.projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await activateProject({
    name: elements.projectNameInput.value.trim(),
    description: elements.projectDescriptionInput.value.trim(),
    keywords: splitKeywords(elements.projectKeywordsInput.value),
    sources: getSelectedSources(),
    latency_profile: elements.projectLatencyInput.value,
    include_official_only: elements.officialOnlyInput.checked,
  });
});

elements.loadDefaultProjectButton.addEventListener("click", async () => {
  await activateProject(state.defaults[0]);
});

elements.projectSearchInput.addEventListener("input", renderProjectLibrary);
elements.launchCustomProjectButton.addEventListener("click", async () => {
  const project = buildCustomProjectFromQuery(elements.projectSearchInput.value);
  if (project) {
    await activateProject(project);
  }
});

elements.searchInput.addEventListener("input", renderExplorer);
elements.sourceFilter.addEventListener("change", renderExplorer);

function formatTimestamp(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

initialize();