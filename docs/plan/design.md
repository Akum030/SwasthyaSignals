# Design Document: SwasthyaSignals

## Overview

The core design decision is to build the MVP around a no-key acquisition mesh instead of waiting for platform partnerships. That mesh combines:

- public patient chatter,
- open-web validation,
- Indian official notices,
- open government datasets.

This gives the prototype a real refresh loop now, while preserving a clean path to richer connectors later.

## Architecture

```text
Reddit JSON ----->
Google News RSS ->
YouTube RSS ----->
Telegram /s/ ---->
NHM updates ----->  normalize -> enrich -> filter -> signal cards -> FastAPI -> static frontend
CDSCO PDFs ------>
data.gov.in RSS ->
```

## Source Acquisition Strategy

### 1. Reddit

- Access pattern: public JSON endpoints
- Current method:
  - health subreddit listings
  - targeted keyword search queries
- Why it matters: captures patient-side symptom, medication, and quality-of-life narratives before official reporting
- Risk: noisy and anecdotal, so it is treated as early evidence only

### 2. Google News RSS

- Access pattern: public RSS search
- Current method: India-focused health-risk queries with 30-day lookback
- Why it matters: creates fast corroboration without paid media APIs
- Risk: aggregator bias and uneven topic coverage

### 3. CDSCO

- Access pattern: homepage PDF notices
- Current method: filter for quality, complaint, biologics, vaccine, medical device, and safety themes
- Current enrichment: bounded PDF text extraction for downstream keyword matching and explainability
- Why it matters: provides Indian drug-safety and regulatory grounding
- Risk: homepage structure may change and PDF formatting can still degrade extraction quality

### 4. National Health Mission

- Access pattern: public website anchors and PDF program documents
- Current method: filter for NP-NCD, MIS, campaigns, operational guidelines, and public-health programs
- Current enrichment: bounded PDF text extraction for program and guideline documents
- Why it matters: gives institutional public-health program context beyond pure drug regulation
- Risk: broader NHM content requires active filtering to avoid noise

### 5. data.gov.in

- Access pattern: public RSS feed
- Current method: filter for health, disease, hospital, immunization, and air-quality datasets
- Why it matters: supplies authentic baseline context that strengthens the India-first story
- Risk: baseline datasets are contextual rather than real-time signals

### 6. YouTube

- Access pattern: public channel handle pages resolved to open RSS feeds
- Current method: curated health and expert channels only, with recent titles and descriptions ingested
- Why it matters: adds explainer and clinician-driven signal corroboration without requiring the YouTube Data API
- Risk: only works well for curated public channels and many videos have shallow descriptions

### 7. Telegram

- Access pattern: public `/s/` channel mirrors
- Current method: curated public channels only, extracting recent message text and permalinks from open HTML
- Why it matters: captures broadcast-style government and campaign updates that do not reliably surface in RSS
- Risk: many Telegram handles expose only contact pages, so the allowlist must stay curated

### Deferred Connectors

- MoHFW homepage: currently too JS-heavy for the no-JS MVP path
- Discord and X: useful, but access and moderation constraints make them phase-two connectors

## Data Model

```python
@dataclass(slots=True)
class ContentItem:
    source: str
    source_label: str
    title: str
    body: str
    url: str
    published_at: str | None
    region: str = "Unknown"
    official: bool = False
    language: str = "unknown"
    sentiment: str = "neutral"
    adr_like: bool = False
    entities: dict[str, list[str]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
```

## Processing Pipeline

1. Fetch source items with source-specific collectors.
2. Normalize text and mask obvious phone and email data.
3. Detect coarse language and infer region.
4. Extract lightweight health entities using curated lexicons.
5. Score sentiment and classify ADR-like patterns.
6. Extract bounded text from official PDFs where available.
7. Filter out low-signal or obviously irrelevant evidence.
8. Augment project views with focused live Reddit and Google News searches derived from the active brief.
9. Group evidence into explainable signal cards.
10. Serve both raw-ish evidence snippets and project-scoped analysis to the frontend.

## Why This Is Harder To Copy Than A Basic Scraper

- It does not rely on a single API or a single scraping trick.
- It intentionally mixes evidence classes: chatter, validation, regulation, and baselines.
- It treats “real today” as a system design constraint.
- It exposes risks and gaps instead of pretending to have perfect coverage.

## Near-Term Design Upgrades

1. Expand synonym dictionaries for Indian brands, Hindi phrases, and regional drug references.
2. Add stronger project-aware ingestion so the system can intensify specific queries for the selected brief with less social noise.
3. Add state-level baselines from NFHS and more data.gov.in feeds.