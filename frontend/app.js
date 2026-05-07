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
  projectLibraryStatus: document.getElementById("projectLibraryStatus"),
  projectGallery: document.getElementById("projectGallery"),
  overviewHeadline: document.getElementById("overviewHeadline"),
  overviewBody: document.getElementById("overviewBody"),
  overviewStats: document.getElementById("overviewStats"),
  launchCustomProjectButton: document.getElementById("launchCustomProjectButton"),
  sourceCheckboxes: document.getElementById("sourceCheckboxes"),
  sourceRootList: document.getElementById("sourceRootList"),
  sourceRootStatus: document.getElementById("sourceRootStatus"),
  officialOnlyInput: document.getElementById("officialOnlyInput"),
  loadDefaultProjectButton: document.getElementById("loadDefaultProjectButton"),
  searchInput: document.getElementById("searchInput"),
  explorerStatus: document.getElementById("explorerStatus"),
  sourceFilter: document.getElementById("sourceFilter"),
};

async function requestJson(path, options = {}) {
  const timeoutMs = options.timeoutMs ?? 20000;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function showDashboardError(message) {
  elements.metricGrid.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function getStartupProject() {
  try {
    const savedProject = window.localStorage.getItem("swasthyaSignals.project");
    return savedProject ? JSON.parse(savedProject) : null;
  } catch {
    return null;
  }
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


function wrapEvidence(text, terms) {
  if (!text) return "";
  if (!terms || terms.length === 0) return text;
  let safe = escapeHtml(text);
  terms.forEach(t => {
    if (!t) return;
    const r = new RegExp('('+t+')', 'gi');
    safe = safe.replace(r, '<mark style="background:var(--amber-soft); color:var(--amber); font-weight:bold; padding:0 4px; border-radius:4px;">$1</mark>');
  });
  return safe;
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

function getSourceCatalogEntry(sourceName) {
  return (state.research?.source_catalog ?? []).find((entry) => entry.name === sourceName) ?? null;
}

function findTrackedResource(entry, label) {
  const target = String(label ?? "").trim().toLowerCase();
  if (!target) {
    return null;
  }
  return (entry?.resource_links ?? []).find(
    (resource) => String(resource.label ?? "").trim().toLowerCase() === target,
  ) ?? null;
}

function getActiveSourceCatalog() {
  const activeSourceNames = state.selectedProject?.sources?.length
    ? state.selectedProject.sources
    : getMvpSourceNames();
  return (state.research?.source_catalog ?? []).filter((entry) => activeSourceNames.includes(entry.name));
}

function buildSourceOrigin(item) {
  const sourceName = String(item?.source ?? "");
  const sourceLabel = String(item?.source_label ?? "").trim();
  const entry = getSourceCatalogEntry(sourceName);
  const fallback = {
    label: entry?.label ?? sourceLabel ?? "Source root",
    url: entry?.resource_url ?? item?.url ?? "#",
  };

  if (sourceName === "youtube" || sourceName === "telegram") {
    const channelLabel = sourceLabel.split(":").slice(1).join(":").trim();
    const tracked = findTrackedResource(entry, channelLabel);
    return {
      label: channelLabel ? `${sourceName === "youtube" ? "Channel" : "Broadcast"}: ${channelLabel}` : fallback.label,
      url: tracked?.url ?? fallback.url,
    };
  }

  if (sourceName === "reddit") {
    if (sourceLabel.toLowerCase().startsWith("search:")) {
      const query = sourceLabel.slice("search:".length).trim();
      return {
        label: query ? `Reddit query: ${query}` : fallback.label,
        url: query ? `https://www.reddit.com/search/?q=${encodeURIComponent(query)}` : fallback.url,
      };
    }
    if (sourceLabel.toLowerCase().startsWith("r/")) {
      const subreddit = sourceLabel.slice(2).trim();
      const tracked = findTrackedResource(entry, sourceLabel);
      return {
        label: subreddit ? `Subreddit: r/${subreddit}` : fallback.label,
        url: tracked?.url ?? (subreddit ? `https://www.reddit.com/r/${encodeURIComponent(subreddit)}/` : fallback.url),
      };
    }
  }

  if (sourceName === "google_news") {
    const query = sourceLabel.split(":").slice(1).join(":").trim();
    return {
      label: query ? `Google News query: ${query}` : fallback.label,
      url: query
        ? `https://news.google.com/search?q=${encodeURIComponent(query)}&hl=en-IN&gl=IN&ceid=IN:en`
        : fallback.url,
    };
  }

  return fallback;
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
  state.selectedSignal = null;
  hydrateForm(project);
  window.localStorage.setItem("swasthyaSignals.project", JSON.stringify(state.selectedProject));
  renderProjectOptions();
  renderProjectLibrary();

  const heroForm = document.getElementById("mainHeroSearch");
  if (heroForm) {
    heroForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const val = document.getElementById("heroSymptomInput").value.trim();
      const proj = buildCustomProjectFromQuery(val);
      if (proj) {
        document.getElementById("heroSymptomInput").blur();
        document.querySelector("#mainHeroSearch button").textContent = "Scanning...";
        await activateProject(proj);
        document.querySelector("#mainHeroSearch button").textContent = "Scan Live Reality →";
      }
    });
  }

  renderProjectLoadingState(project);
  await analyzeSelectedProject(false);
}

function renderProjectOptions() {
  elements.projectSelect.innerHTML = "";
  const placeholderOption = document.createElement("option");
  placeholderOption.value = "";
  placeholderOption.textContent = state.defaults.length
    ? "Select a project brief"
    : "Loading project briefs...";
  placeholderOption.disabled = true;
  elements.projectSelect.append(placeholderOption);

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
  elements.projectSelect.disabled = state.defaults.length === 0;
  elements.projectSelect.value = selectedIndex >= 0
    ? String(selectedIndex)
    : state.selectedProject
      ? "custom"
      : "";
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
  if (!project) {
    elements.projectName.textContent = "Choose a project brief";
    elements.projectDescription.textContent = "Pick a preset or search your own issue below to open the dashboard.";
    elements.latencyProfile.textContent = "Ready";
    return;
  }
  elements.projectName.textContent = project.name;
  elements.projectDescription.textContent = project.description;
  elements.latencyProfile.textContent = project.latency_profile;
}

function renderProjectLoadingState(project) {
  const scopeName = project?.name ?? "this project";
  updateProjectBrief(project);
  renderSourceRoots();
  renderOverview();
  elements.metricGrid.innerHTML = '<div class="empty-state">Loading project metrics...</div>';
  elements.timelineChart.innerHTML = '<div class="empty-state">Loading time-series view...</div>';
  elements.compareBars.innerHTML = '<div class="empty-state">Loading comparison view...</div>';
  elements.sourceStatusList.innerHTML = '<div class="empty-state">Refreshing source health...</div>';
  elements.regionList.innerHTML = '<div class="empty-state">Loading region breakdown...</div>';
  elements.signalGrid.innerHTML = `<div class="empty-state">Building the signal board for ${escapeHtml(scopeName)}...</div>`;
  renderSignalDetail(null);
  elements.explorerStatus.textContent = `Loading evidence for ${scopeName}...`;
  elements.itemList.innerHTML = `<div class="empty-state">Loading the evidence explorer for ${escapeHtml(scopeName)}...</div>`;
}

function renderSnapshotMeta() {
  const generatedAt = state.snapshot?.generated_at;
  elements.lastSweep.textContent = generatedAt ? formatTimestamp(generatedAt) : "Awaiting refresh";
}

function renderOverview() {
  const project = state.selectedProject;
  const metrics = state.analysis?.metrics ?? null;
  const activeSources = getActiveSourceCatalog();
  const sourceStatuses = state.snapshot?.source_status ?? [];
  const liveSourceCount = sourceStatuses.filter((status) => status.ok && status.item_count > 0).length;

  if (!project) {
    elements.overviewHeadline.textContent = "Choose a project to open the radar";
    elements.overviewBody.textContent = "The top rail will summarize signal count, evidence scope, and source readiness as soon as a project is loaded.";
    elements.overviewStats.innerHTML = [
      ["Latency", "Ready", "Select or type a brief"],
      ["Sources", "0", "No active sources yet"],
      ["Signals", "0", "Explainable alerts appear here"],
      ["Explorer", "Scoped", "Search stays inside one brief"],
    ].map(
      ([label, value, detail]) => `
        <article class="overview-stat">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
          <p>${escapeHtml(detail)}</p>
        </article>
      `,
    ).join("");
    return;
  }

  if (metrics) {
    elements.overviewHeadline.textContent = `${metrics.signal_count} explainable signals built from ${metrics.item_count} evidence items`;
    elements.overviewBody.textContent = `${project.description} This brief currently mixes ${metrics.india_count} India-coded items with ${metrics.official_count} official anchors.`;
  } else {
    elements.overviewHeadline.textContent = `Loading ${project.name}`;
    elements.overviewBody.textContent = "The brief shell, source roots, and project context are already visible while slower analysis finishes in the background.";
  }

  const overviewCards = [
    {
      label: "Latency",
      value: project.latency_profile ?? "Realtime",
      detail: "Refresh rhythm for this brief",
    },
    {
      label: "Sources",
      value: String(activeSources.length || project.sources?.length || 0),
      detail: liveSourceCount > 0 ? `${liveSourceCount} sources active in the latest sweep` : "Waiting for the next live sweep",
    },
    {
      label: "Signals",
      value: metrics ? String(metrics.signal_count) : "Loading",
      detail: metrics ? "Cards are ready for explainability review" : "Signal board is hydrating",
    },
    {
      label: "Explorer",
      value: metrics ? `${metrics.item_count} items` : "Scoped",
      detail: metrics ? "Search and provenance stay inside this brief" : "Search remains project-only",
    },
  ];

  elements.overviewStats.innerHTML = overviewCards
    .map(
      (card) => `
        <article class="overview-stat">
          <span>${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
          <p>${escapeHtml(card.detail)}</p>
        </article>
      `,
    )
    .join("");
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
  if (!state.defaults.length) {
    elements.projectLibraryStatus.textContent = "Loading project presets...";
    elements.projectGallery.innerHTML = '<div class="empty-state">Loading the project library...</div>';
    return;
  }

  const query = elements.projectSearchInput.value.trim().toLowerCase();
  const visibleProjects = state.defaults
    .map((project, defaultIndex) => ({ project, defaultIndex }))
    .filter(({ project }) => {
      if (!query) {
        return true;
      }
      const merged = `${project.name} ${project.description} ${(project.keywords ?? []).join(" ")}`.toLowerCase();
      return merged.includes(query);
    });
  const customProject = buildCustomProjectFromQuery(elements.projectSearchInput.value);
  const statusBits = [`Showing ${visibleProjects.length} of ${state.defaults.length} presets`];
  if (customProject) {
    statusBits.push("Press Enter or use Run typed issue to launch the custom brief");
  } else if (!query) {
    statusBits.push("Type any issue to create a custom brief");
  }
  elements.projectLibraryStatus.textContent = statusBits.join(" • ");

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
    ...visibleProjects.map(({ project, defaultIndex }) => {
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
            <button class="action-button secondary small-button" type="button" data-project-index="${defaultIndex}">Load project</button>
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
              <span class="bg-slate-100 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">${signal.region}</span>
              ${tags}
            </div>
            <h3 class="font-bold text-slate-900 text-lg mb-2 leading-tight">${signal.title}</h3>
            <p class="text-sm text-slate-600 line-clamp-3 mb-4">${signal.summary}</p>
            <div class="flex items-center justify-between mt-auto pt-3 border-t border-slate-100 text-xs font-semibold text-slate-500">
              <span class="flex items-center gap-1"><svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg> ${signal.evidence_count} proofs</span>
              <span class="text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full flex items-center gap-1">Alert ${signal.confidence}</span>
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

function renderSourceRoots() {
  const activeSources = getActiveSourceCatalog();
  if (!activeSources.length) {
    elements.sourceRootStatus.textContent = "Loading source roots...";
    elements.sourceRootList.innerHTML = '<div class="empty-state">Source roots will appear once the project and research catalog load.</div>';
    return;
  }

  const projectName = state.selectedProject?.name ?? "this project";
  elements.sourceRootStatus.textContent = `${activeSources.length} active source roots for ${projectName}`;
  elements.sourceRootList.innerHTML = activeSources
    .map((source) => {
      const primaryUrl = escapeHtml(safeExternalUrl(source.resource_url));
      const trackedLinks = (source.resource_links ?? [])
        .slice(0, 3)
        .map((resource) => {
          const safeUrl = escapeHtml(safeExternalUrl(resource.url));
          return `<a class="resource-chip" href="${safeUrl}" target="_blank" rel="noreferrer">${escapeHtml(resource.label)}</a>`;
        })
        .join("");
      return `
        <article class="source-root-card">
          <div class="catalog-meta">
            <span>${source.mvp ? "Live now" : "Stretch"}</span>
            <span>${escapeHtml(source.name)}</span>
          </div>
          <h3>${escapeHtml(source.label)}</h3>
          <p>${escapeHtml(source.method)}</p>
          <div class="item-actions">
            <a class="link-button secondary-link" href="${primaryUrl}" target="_blank" rel="noreferrer">Open source root</a>
          </div>
          ${trackedLinks ? `<div class="resource-chip-row">${trackedLinks}</div>` : ""}
        </article>
      `;
    })
    .join("");
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
  const scopeName = state.selectedProject?.name ?? "current project";
  const filtered = items.filter((item) => {
    const merged = `${cleanDisplayText(item.title)} ${cleanDisplayText(item.body)}`.toLowerCase();
    const matchesQuery = !query || merged.includes(query);
    const matchesSource = sourceFilter === "all" || item.source === sourceFilter;
    return matchesQuery && matchesSource;
  });

  const statusBits = [`${filtered.length} of ${items.length} evidence items`, scopeName];
  if (query) {
    statusBits.push(`query: ${query}`);
  }
  if (sourceFilter !== "all") {
    statusBits.push(`source: ${sourceFilter}`);
  }
  elements.explorerStatus.textContent = statusBits.join(" • ");

  if (!filtered.length) {
    elements.itemList.innerHTML = `
      <div class="empty-state">
        No evidence items match the current filters inside ${escapeHtml(scopeName)}.
        ${query ? `Try clearing "${escapeHtml(query)}" or switch to another project.` : "Try another source filter or switch projects."}
      </div>
    `;
    return;
  }

  elements.itemList.innerHTML = filtered
    .map((item) => {
      const safeTitle = escapeHtml(cleanDisplayText(item.title));
      const safeBody = escapeHtml(cleanDisplayText(item.body || "No body text available."));
      const safeSourceLabel = escapeHtml(item.source_label || item.source);
      const safeRegion = escapeHtml(item.region);
      const safeSentiment = escapeHtml(item.sentiment);
      const safeUrl = escapeHtml(safeExternalUrl(item.url));
      const sourceOrigin = buildSourceOrigin(item);
      const safeOriginLabel = escapeHtml(sourceOrigin.label);
      const safeOriginUrl = escapeHtml(safeExternalUrl(sourceOrigin.url));
      const chips = Object.values(item.entities ?? {})
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
          <p class="item-trace"><strong>Fetched via:</strong> ${safeSourceLabel}</p>
          <p class="item-trace"><strong>Root source:</strong> ${safeOriginLabel}</p>
          <div class="chip-row">${chips || '<span class="chip alt">No matched entities</span>'}</div>
          <div class="item-actions">
            <a class="link-button primary-link" href="${safeUrl}" target="_blank" rel="noreferrer">Open fetched item</a>
            <a class="link-button secondary-link" href="${safeOriginUrl}" target="_blank" rel="noreferrer">Open source root</a>
          </div>
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

  const heroForm = document.getElementById("mainHeroSearch");
  if (heroForm) {
    heroForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const val = document.getElementById("heroSymptomInput").value.trim();
      const proj = buildCustomProjectFromQuery(val);
      if (proj) {
        document.getElementById("heroSymptomInput").blur();
        document.querySelector("#mainHeroSearch button").textContent = "Scanning...";
        await activateProject(proj);
        document.querySelector("#mainHeroSearch button").textContent = "Scan Live Reality →";
      }
    });
  }

  updateProjectBrief(state.selectedProject);
  renderSourceRoots();
  renderSnapshotMeta();
  renderOverview();
  renderLaneStrip();
  renderMetrics();
  renderTimeline();
  renderComparison();
  renderSignals();
  populateSourceFilter();
  renderExplorer();
  renderResearch();
}

async function refreshSnapshot() {
  state.snapshot = await requestJson("/api/v1/snapshot", { timeoutMs: 70000 });
}

async function refreshSnapshotLive() {
  state.snapshot = await requestJson("/api/v1/snapshot?refresh=true", { timeoutMs: 45000 });
}

async function analyzeSelectedProject(refresh = false) {
  state.analysis = await requestJson(`/api/v1/projects/analyze${refresh ? "?refresh=true" : ""}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.selectedProject),
    timeoutMs: refresh ? 90000 : 70000,
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

  const heroForm = document.getElementById("mainHeroSearch");
  if (heroForm) {
    heroForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const val = document.getElementById("heroSymptomInput").value.trim();
      const proj = buildCustomProjectFromQuery(val);
      if (proj) {
        document.getElementById("heroSymptomInput").blur();
        document.querySelector("#mainHeroSearch button").textContent = "Scanning...";
        await activateProject(proj);
        document.querySelector("#mainHeroSearch button").textContent = "Scan Live Reality →";
      }
    });
  }

    renderSourceCheckboxes();

    state.selectedProject = getStartupProject() ?? state.defaults[0] ?? null;

    if (!state.selectedProject) {
      throw new Error("No project briefs are available yet.");
    }

    hydrateForm(state.selectedProject);
    renderProjectLoadingState(state.selectedProject);
    await refreshSnapshot();
    await analyzeSelectedProject(false);
  } catch (error) {
    showDashboardError(`Unable to load the dashboard: ${error.message}`);
    updateProjectBrief(null);
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
  try {
    await refreshSnapshotLive();
    await analyzeSelectedProject(false);
  } catch (error) {
    if (state.selectedProject) {
      elements.projectDescription.textContent = `${state.selectedProject.description} Showing the last saved snapshot while live refresh catches up.`;
    }
    if (!state.analysis) {
      showDashboardError(`Live refresh is not available right now: ${error.message}`);
    }
  } finally {
    elements.refreshButton.disabled = false;
    elements.refreshButton.textContent = "Refresh live radar";
  }
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
elements.projectSearchInput.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  const project = buildCustomProjectFromQuery(elements.projectSearchInput.value);
  if (project) {
    await activateProject(project);
  }
});
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