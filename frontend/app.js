/* SwasthyaSignals — clean frontend v3 (2026-05-08) */
"use strict";

const state = { defaults: [], research: null, analysis: null, keywords: [], lastQuery: "", selectedSignal: null };

const el = {
  topbar: document.getElementById("topbar"),
  topbarLogoLink: document.getElementById("topbarLogoLink"),
  topbarForm: document.getElementById("topbarSearchForm"),
  topbarInput: document.getElementById("topbarInput"),
  heroSection: document.getElementById("heroSection"),
  heroForm: document.getElementById("heroSearchForm"),
  heroInput: document.getElementById("heroInput"),
  loading: document.getElementById("loadingState"),
  loadingTitle: document.getElementById("loadingTitle"),
  loadingSub: document.getElementById("loadingSub"),
  errorState: document.getElementById("errorState"),
  errorMsg: document.getElementById("errorMsg"),
  errorRetryBtn: document.getElementById("errorRetryBtn"),
  results: document.getElementById("resultsSection"),
  queryDisplay: document.getElementById("queryDisplay"),
  metaPills: document.getElementById("metaPills"),
  signalList: document.getElementById("signalList"),
  signalCount: document.getElementById("signalCount"),
  signalDetail: document.getElementById("signalDetail"),
  evidenceList: document.getElementById("evidenceList"),
  evidenceCount: document.getElementById("evidenceCount"),
  evidenceStatus: document.getElementById("evidenceStatus"),
  evidenceSearch: document.getElementById("evidenceSearchInput"),
  evidenceSource: document.getElementById("evidenceSourceFilter"),
};

/* ---- Utils ---- */
function esc(v) {
  return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
}
function safeUrl(v) {
  try { const u = new URL(String(v ?? ""), location.origin); return (u.protocol==="http:"||u.protocol==="https:") ? u.href : "#"; } catch { return "#"; }
}
function cleanText(v) { return String(v ?? "").replace(/[\r\n]+/g," ").replace(/\s+/g," ").trim(); }
function highlight(text, kws) {
  if (!text || !kws.length) return esc(text);
  let s = esc(text);
  kws.forEach(k => {
    if (!k || k.length < 2) return;
    s = s.replace(new RegExp("("+k.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","gi"),"<mark>$1</mark>");
  });
  return s;
}
function sourceBadgeClass(src) {
  return ["reddit","google_news","youtube","telegram","cdsco","nhm","data_gov"].includes(src) ? src : "default";
}
function formatSourceLabel(src) {
  return {reddit:"Reddit",google_news:"Google News",youtube:"YouTube",telegram:"Telegram",cdsco:"CDSCO",nhm:"NHM",data_gov:"data.gov.in"}[src] ?? (src||"Source");
}
function confBadge(n) {
  n = Number(n); const cls = n>=70?"high":n>=40?"med":"low"; const lbl = n>=70?"High":n>=40?"Medium":"Low";
  return `<span class="sc-conf ${cls}">${lbl} ${n}</span>`;
}
function confidenceWord(n) {
  n = Number(n);
  return n >= 70 ? "High confidence" : n >= 40 ? "Medium confidence" : "Low confidence";
}
function truncate(text, limit) {
  const value = cleanText(text);
  return value.length > limit ? value.slice(0, limit - 1) + "…" : value;
}
function hostLabel(value) {
  try { return new URL(String(value), location.origin).hostname.replace(/^www\./, ""); }
  catch { return "source"; }
}
function formatTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
function evidenceKind(item) {
  if (item?.official) return "Official reference";
  if (item?.source === "reddit") return "Community thread";
  if (item?.source === "youtube") return "Video mention";
  if (item?.source === "google_news") return "News coverage";
  if (item?.source === "telegram") return "Telegram post";
  if (item?.source === "cdsco" || item?.source === "nhm" || item?.source === "data_gov") return "Public document";
  return "Web evidence";
}
function primaryActionLabel(item) {
  if (item?.official) return "Open official source";
  if (item?.source === "reddit") return "Open Reddit thread";
  if (item?.source === "youtube") return "Open video source";
  if (item?.source === "google_news") return "Open article or listing";
  if (item?.source === "telegram") return "Open Telegram post";
  return "Open original evidence";
}
function secondaryActionLabel(item) {
  if (!item?.source) return "Open source root";
  return `Browse ${formatSourceLabel(item.source)}`;
}
function attachMotionCards(root = document) {
  if (!window.matchMedia("(hover: hover)").matches) return;
  const scoped = root.matches?.("[data-tilt-card]") ? [root, ...root.querySelectorAll("[data-tilt-card]")] : root.querySelectorAll("[data-tilt-card]");
  scoped.forEach(card => {
    if (card.dataset.motionBound === "1") return;
    card.dataset.motionBound = "1";
    const reset = () => {
      card.style.setProperty("--card-tilt-x", "0deg");
      card.style.setProperty("--card-tilt-y", "0deg");
      card.style.setProperty("--card-glow-x", "50%");
      card.style.setProperty("--card-glow-y", "50%");
    };
    card.addEventListener("mousemove", event => {
      const rect = card.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      card.style.setProperty("--card-tilt-x", `${((0.5 - py) * 8).toFixed(2)}deg`);
      card.style.setProperty("--card-tilt-y", `${((px - 0.5) * 10).toFixed(2)}deg`);
      card.style.setProperty("--card-glow-x", `${(px * 100).toFixed(1)}%`);
      card.style.setProperty("--card-glow-y", `${(py * 100).toFixed(1)}%`);
    });
    card.addEventListener("mouseleave", reset);
    reset();
  });
}
async function fetchJson(path, opts={}) {
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? 90000);
  try {
    const r = await fetch(path, { ...opts, signal: ctrl.signal });
    if (!r.ok) throw new Error("HTTP "+r.status);
    return r.json();
  } catch(e) { if (e.name==="AbortError") throw new Error("Request timed out"); throw e; }
  finally { clearTimeout(tid); }
}
function buildProject(query) {
  const q = String(query ?? "").trim().replace(/\s+/g," ");
  if (!q) return null;
  const parts = q.toLowerCase().split(/[^a-z0-9]+/).filter(p=>p.length>2);
  const keywords = [...new Set([q.toLowerCase(),...parts])].slice(0,8);
  const sources = state.research ? state.research.source_catalog.filter(s=>s.mvp).map(s=>s.name) : ["reddit","google_news","youtube","telegram","cdsco","nhm"];
  return { name: q+" watch", description: "Track live evidence for "+q+" across patient chatter and Indian official context.", keywords, sources, latency_profile: "Realtime", include_official_only: false };
}

/* ---- UI state ---- */
function showHero() {
  el.heroSection.style.display = "";
  el.loading.classList.remove("visible");
  el.errorState.classList.remove("visible");
  el.results.classList.remove("visible");
  el.topbar.classList.remove("visible");
}
function showLoading(title, sub) {
  el.heroSection.style.display = "none";
  el.loading.classList.add("visible");
  el.errorState.classList.remove("visible");
  el.results.classList.remove("visible");
  el.topbar.classList.add("visible");
  el.loadingTitle.textContent = title || "Scanning live sources...";
  el.loadingSub.textContent = sub || "Reading patient chatter, government data, and expert sources";
}
function showError(msg) {
  el.loading.classList.remove("visible");
  el.errorState.classList.add("visible");
  el.errorMsg.textContent = msg || "Something went wrong.";
}

/* ---- Skeletons ---- */
function showSkeletons() {
  const sk = (w="w100") => `<div class="sk h12 ${w}"></div>`;
  el.signalList.innerHTML = Array(4).fill(0).map(()=>`<div class="skeleton-card">${sk("w70")}${sk("w100")}${sk("w40")}</div>`).join("");
  el.evidenceList.innerHTML = Array(5).fill(0).map(()=>`<div class="skeleton-card">${sk("w40")}${sk("w70")}${sk("w100")}${sk("w100")}${sk("w60")}</div>`).join("");
}

/* ---- Render: signals ---- */
function renderSignals(signals) {
  el.signalCount.textContent = signals.length + (signals.length===1?" signal":" signals");
  if (!signals.length) {
    el.signalList.innerHTML = `<div class="empty-state">No health signals detected for this keyword.<br>Try a more specific term like a drug name or disease.</div>`;
    el.signalDetail.classList.remove("visible"); return;
  }
  el.signalList.innerHTML = signals.map((sig, idx) => {
    const active = state.selectedSignal?.title === sig.title ? " active" : "";
    const score = Number(sig.confidence ?? 0);
    const level = score >= 70 ? "high" : score >= 40 ? "med" : "low";
    const tags = (sig.tags||[]).slice(0,3).map(t=>`<span class="sc-tag">${esc(t)}</span>`).join("");
    const leadTag = cleanText((sig.tags || [])[0] || "Detected pattern");
    return `<article class="signal-card${active}" data-title="${esc(sig.title)}" data-tilt-card tabindex="0" role="button" aria-pressed="${active ? "true" : "false"}">
      <div class="sc-hero">
        <div class="sc-meter ${level}">
          <span class="sc-meter-ring"></span>
          <strong class="sc-meter-value">${score}</strong>
          <span class="sc-meter-label">${esc(confidenceWord(score))}</span>
        </div>
        <div class="sc-copy">
          <div class="sc-topline">
            <span class="sc-region">${esc(sig.region || "India")}</span>
            <span class="sc-evidence">${sig.evidence_count} linked proofs</span>
          </div>
          <p class="sc-kicker">Signal ${idx + 1} · ${esc(leadTag)}</p>
          <h3 class="sc-title">${esc(sig.title)}</h3>
        </div>
      </div>
      <p class="sc-summary">${esc(truncate(sig.summary, 170))}</p>
      <div class="sc-footer">${tags}<span class="sc-action-hint">Select to inspect why this signal fired</span></div>
    </article>`;
  }).join("");
  el.signalList.querySelectorAll(".signal-card").forEach(card => {
    const activate = () => {
      const sig = signals.find(s=>s.title===card.dataset.title); if (!sig) return;
      state.selectedSignal = sig;
      el.signalList.querySelectorAll(".signal-card").forEach(c => {
        c.classList.remove("active");
        c.setAttribute("aria-pressed", "false");
      });
      card.classList.add("active");
      card.setAttribute("aria-pressed", "true");
      renderSignalDetail(sig);
    };
    card.addEventListener("click", activate);
    card.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });
  if (!state.selectedSignal) { state.selectedSignal = signals[0]; el.signalList.querySelector(".signal-card")?.classList.add("active"); renderSignalDetail(signals[0]); }
  else renderSignalDetail(state.selectedSignal);
  attachMotionCards(el.signalList);
}

function renderSignalDetail(sig) {
  if (!sig) { el.signalDetail.classList.remove("visible"); return; }
  el.signalDetail.classList.add("visible");
  const links = [...(sig.official_references||[]),...(sig.example_urls||[])].slice(0,6);
  const tagList = [sig.region, ...(sig.tags || []).slice(0, 3)].filter(Boolean);
  const score = Number(sig.confidence ?? 0);
  const renderedLinks = links.length ? links.map((url, idx) => {
    const safe = safeUrl(url); if (safe === "#") return "";
    let lbl = "Open source";
    let kind = "Direct source";
    try {
      const h = new URL(safe).hostname.replace(/^www\./, "");
      if (h.includes("reddit")) { lbl = "Open Reddit thread"; kind = "Community discussion"; }
      else if (h.includes("youtube")) { lbl = "Open YouTube video"; kind = "Video evidence"; }
      else if (h.includes("cdsco")) { lbl = "Open CDSCO reference"; kind = "Official reference"; }
      else if (h.includes("nhm")) { lbl = "Open NHM source"; kind = "Official reference"; }
      else if (h.includes("data.gov")) { lbl = "Open data.gov.in entry"; kind = "Public dataset"; }
      else if (h.includes("news.google")) { lbl = "Open Google News listing"; kind = "News listing"; }
      else { lbl = `Open ${h}`; kind = "External source"; }
      return `<a class="detail-link detail-link-card" href="${esc(safe)}" target="_blank" rel="noreferrer" data-tilt-card>
        <span class="detail-link-index">${String(idx + 1).padStart(2, "0")}</span>
        <span class="detail-link-copy">
          <strong class="detail-link-label">${esc(lbl)}</strong>
          <span class="detail-link-meta">${esc(kind)} · ${esc(h)}</span>
        </span>
        <svg class="dl-icon" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
      </a>`;
    } catch { return ""; }
  }).join("") : `<div class="empty-state">No direct source links for this signal yet.</div>`;
  el.signalDetail.innerHTML = `<div class="detail-shell" data-tilt-card>
    <div class="detail-head">
      <div>
        <p class="detail-label">Selected signal</p>
        <h3 class="detail-title">${esc(sig.title)}</h3>
      </div>
      <div class="detail-metrics">${confBadge(score)}<span class="detail-pill">${sig.evidence_count} evidence links</span></div>
    </div>
    <p class="detail-summary">${esc(cleanText(sig.summary))}</p>
    ${tagList.length ? `<div class="detail-tags">${tagList.map(tag => `<span class="sc-tag">${esc(tag)}</span>`).join("")}</div>` : ""}
    <div class="detail-links">${renderedLinks}</div>
  </div>`;
  attachMotionCards(el.signalDetail);
}

/* ---- Render: evidence ---- */
function buildSourceUrl(item) {
  if (!item) return "#";
  const s=item.source, lbl=item.source_label||"";
  if (s==="reddit") { if (lbl.toLowerCase().startsWith("r/")) return "https://www.reddit.com/"+lbl; const q=lbl.replace(/^search:/i,"").trim(); return q?"https://www.reddit.com/search/?q="+encodeURIComponent(q):"https://www.reddit.com"; }
  if (s==="google_news") { const q=lbl.split(":").pop().trim(); return q?"https://news.google.com/search?q="+encodeURIComponent(q)+"&hl=en-IN&gl=IN":"https://news.google.com"; }
  if (s==="youtube") return "https://www.youtube.com";
  if (s==="telegram") return "https://t.me";
  if (s==="cdsco") return "https://cdsco.gov.in";
  if (s==="nhm") return "https://nhm.gov.in";
  if (s==="data_gov") return "https://data.gov.in";
  return safeUrl(item.url);
}
function populateSourceFilter(items) {
  const sources = [...new Set(items.map(i=>i.source).filter(Boolean))];
  const cur = el.evidenceSource.value;
  el.evidenceSource.innerHTML = `<option value="all">All Sources</option>`+sources.map(s=>`<option value="${esc(s)}">${esc(formatSourceLabel(s))}</option>`).join("");
  if (sources.includes(cur)) el.evidenceSource.value = cur;
}
function renderEvidence(items) {
  const query = el.evidenceSearch.value.trim().toLowerCase();
  const src = el.evidenceSource.value;
  const kws = state.keywords;
  const filtered = items.filter(item => {
    const text = `${cleanText(item.title)} ${cleanText(item.body)}`.toLowerCase();
    return (!query || text.includes(query)) && (src==="all" || item.source===src);
  });
  el.evidenceCount.textContent = filtered.length+" items";
  el.evidenceStatus.textContent = filtered.length < items.length ? `Showing ${filtered.length} of ${items.length} — filter active` : `${items.length} verified evidence items`;
  if (!filtered.length) { el.evidenceList.innerHTML=`<div class="empty-state">No evidence matches this filter.<br>Try clearing the filter above.</div>`; return; }
  el.evidenceList.innerHTML = filtered.map((item,idx) => {
    const srcCls = sourceBadgeClass(item.source);
    const srcLbl = formatSourceLabel(item.source) + (item.source_label?(" · "+item.source_label.split(":").pop().trim()):"");
    const title = cleanText(item.title) || cleanText(item.body).slice(0,80);
    const body = cleanText(item.body||""); const snippet = body.length>320?body.slice(0,320)+"…":body;
    const url = safeUrl(item.url); const rootUrl = buildSourceUrl(item);
    const tags = [item.region,item.sentiment].filter(Boolean);
    const entities = Array.isArray(item.entities) ? item.entities.slice(0,4) : [];
    const timeLabel = formatTime(item.timestamp);
    const kind = evidenceKind(item);
    const host = hostLabel(url !== "#" ? url : rootUrl);
    const primaryLabel = primaryActionLabel(item);
    return `<article class="item-card${item.official ? " official" : ""}" style="animation-delay:${Math.min(idx*.04,.4)}s" data-tilt-card>
      <div class="ic-top">
        <div class="ic-source-group"><span class="ic-index">${String(idx + 1).padStart(2, "0")}</span><span class="ic-source ${srcCls}">${esc(srcLbl)}</span>${item.official?`<span class="ic-official">&#10003; Official</span>`:""}</div>
        <span class="ic-kind">${esc(kind)}</span>
      </div>
      ${title?`<h3 class="ic-title">${highlight(title,kws)}</h3>`:""}
      ${snippet?`<p class="ic-body">${highlight(snippet,kws)}</p>`:""}
      ${entities.length?`<div class="ic-entities">${entities.map(entity=>`<span class="ic-entity">${esc(entity)}</span>`).join("")}</div>`:""}
      ${(tags.length || timeLabel || host)?`<div class="ic-context">${tags.map(t=>`<span class="ic-context-item">${esc(t)}</span>`).join("")}${timeLabel?`<span class="ic-context-item">${esc(timeLabel)}</span>`:""}${host?`<span class="ic-context-item">${esc(host)}</span>`:""}</div>`:""}
      <p class="ic-link-meaning">${esc(primaryLabel)}${host ? ` from ${esc(host)}` : ""}</p>
      <div class="ic-actions">
        ${url!=="#"?`<a class="ic-btn primary" href="${esc(url)}" target="_blank" rel="noreferrer"><svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg> ${esc(primaryLabel)}</a>`:""}
        ${rootUrl!=="#"&&rootUrl!==url?`<a class="ic-btn secondary" href="${esc(rootUrl)}" target="_blank" rel="noreferrer">${esc(secondaryActionLabel(item))}</a>`:""}
      </div>
    </article>`;
  }).join("");
  attachMotionCards(el.evidenceList);
}

/* ---- Meta pills ---- */
function renderMetaPills(metrics) {
  if (!metrics) { el.metaPills.innerHTML=""; return; }
  const pills = [[metrics.item_count+" evidence items","green"],[metrics.signal_count+" signals","green"],[metrics.india_count+" India-specific",""],[metrics.official_count+" official refs",""]];
  el.metaPills.innerHTML = pills.filter(([l])=>!l.startsWith("undefined")&&!l.startsWith("null")).map(([l,c])=>`<span class="results-pill ${c}">${esc(l)}</span>`).join("");
}

/* ---- Main search ---- */
async function doSearch(rawQuery) {
  const query = String(rawQuery||"").trim(); if (!query) return;
  state.lastQuery = query; state.selectedSignal = null;
  state.keywords = query.toLowerCase().split(/[^a-z0-9]+/).filter(p=>p.length>2);
  showLoading(`Scanning for "${query}"...`, "Pulling patient chatter, news, and government data");
  el.topbarInput.value = query; el.heroInput.value = query;
  el.queryDisplay.innerHTML = "&ldquo;"+esc(query)+"&rdquo;";
  const project = buildProject(query);
  try {
    showSkeletons();
    el.loading.classList.remove("visible");
    el.results.classList.add("visible");
    const analysis = await fetchJson("/api/v1/projects/analyze", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(project), timeoutMs:90000 });
    state.analysis = analysis;
    renderMetaPills(analysis.metrics ?? null);
    renderSignals(analysis.signals ?? []);
    populateSourceFilter(analysis.items ?? []);
    renderEvidence(analysis.items ?? []);
  } catch(err) { showError(`Could not scan "${query}": ${err.message}`); }
}

/* ---- Events ---- */
el.heroForm.addEventListener("submit", e => { e.preventDefault(); doSearch(el.heroInput.value); });
el.topbarForm.addEventListener("submit", e => { e.preventDefault(); doSearch(el.topbarInput.value); });
el.topbarLogoLink.addEventListener("click", e => { e.preventDefault(); showHero(); });
document.querySelectorAll(".preset-chip").forEach(chip => chip.addEventListener("click", () => doSearch(chip.dataset.query)));
el.errorRetryBtn.addEventListener("click", () => state.lastQuery ? doSearch(state.lastQuery) : showHero());
el.evidenceSearch.addEventListener("input", () => renderEvidence(state.analysis?.items ?? []));
el.evidenceSource.addEventListener("change", () => renderEvidence(state.analysis?.items ?? []));

/* ---- Init ---- */
(async function init() {
  try {
    const [d,r] = await Promise.all([fetchJson("/api/v1/projects/defaults",{timeoutMs:10000}), fetchJson("/api/v1/research",{timeoutMs:10000})]);
    state.defaults = d.projects ?? []; state.research = r;
  } catch { /* silently ignore */ }
  attachMotionCards(document);
})();