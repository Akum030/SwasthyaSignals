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
  signalDetailSummary: document.getElementById("signalDetailSummary"),
  signalDetailLinks: document.getElementById("signalDetailLinks"),
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
  el.signalList.innerHTML = signals.map(sig => {
    const active = state.selectedSignal?.title === sig.title ? " active" : "";
    const tags = (sig.tags||[]).slice(0,3).map(t=>`<span class="sc-tag t">${esc(t)}</span>`).join("");
    return `<article class="signal-card${active}" data-title="${esc(sig.title)}">
      <div class="sc-top"><span class="sc-title">${esc(sig.title)}</span>${confBadge(sig.confidence)}</div>
      <p class="sc-summary">${esc(cleanText(sig.summary))}</p>
      <div class="sc-footer"><span class="sc-tag">${esc(sig.region)}</span>${tags}<span class="sc-proofs">${sig.evidence_count} proofs</span></div>
    </article>`;
  }).join("");
  el.signalList.querySelectorAll(".signal-card").forEach(card => {
    card.addEventListener("click", () => {
      const sig = signals.find(s=>s.title===card.dataset.title); if (!sig) return;
      state.selectedSignal = sig;
      el.signalList.querySelectorAll(".signal-card").forEach(c=>c.classList.remove("active"));
      card.classList.add("active");
      renderSignalDetail(sig);
    });
  });
  if (!state.selectedSignal) { state.selectedSignal = signals[0]; el.signalList.querySelector(".signal-card")?.classList.add("active"); renderSignalDetail(signals[0]); }
  else renderSignalDetail(state.selectedSignal);
}

function renderSignalDetail(sig) {
  if (!sig) { el.signalDetail.classList.remove("visible"); return; }
  el.signalDetail.classList.add("visible");
  el.signalDetailSummary.textContent = cleanText(sig.summary);
  const links = [...(sig.official_references||[]),...(sig.example_urls||[])].slice(0,6);
  el.signalDetailLinks.innerHTML = links.length ? links.map(url => {
    const safe = safeUrl(url); if (safe==="#") return "";
    let lbl = "Open source";
    try { const h = new URL(safe).hostname.replace(/^www\./,"");
      if (h.includes("reddit")) lbl="Reddit thread";
      else if (h.includes("youtube")) lbl="YouTube video";
      else if (h.includes("cdsco")) lbl="CDSCO official";
      else if (h.includes("nhm")) lbl="NHM source";
      else if (h.includes("data.gov")) lbl="data.gov.in";
      else if (h.includes("news.google")) lbl="Google News";
      else lbl=h; } catch {}
    return `<a class="detail-link" href="${esc(safe)}" target="_blank" rel="noreferrer"><svg class="dl-icon" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>${esc(lbl)}</a>`;
  }).join("") : `<p style="font-size:.83rem;color:var(--ink-f);">No direct source links for this signal.</p>`;
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
    return `<article class="item-card" style="animation-delay:${Math.min(idx*.04,.4)}s">
      <div class="ic-top"><span class="ic-source ${srcCls}">${esc(srcLbl)}</span>${item.official?`<span class="ic-official">&#10003; Official</span>`:""}</div>
      ${title?`<p class="ic-title">${highlight(title,kws)}</p>`:""}
      ${snippet?`<p class="ic-body">${highlight(snippet,kws)}</p>`:""}
      ${tags.length?`<div class="ic-meta">${tags.map(t=>`<span class="ic-tag">${esc(t)}</span>`).join("")}</div>`:""}
      <div class="ic-actions">
        ${url!=="#"?`<a class="ic-btn primary" href="${esc(url)}" target="_blank" rel="noreferrer"><svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg> View original post</a>`:""}
        ${rootUrl!=="#"&&rootUrl!==url?`<a class="ic-btn secondary" href="${esc(rootUrl)}" target="_blank" rel="noreferrer">Open source root</a>`:""}
      </div>
    </article>`;
  }).join("");
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
})();