# SwasthyaSignals

SwasthyaSignals is an India-first social health early warning prototype that fuses live public patient chatter, India-focused open news validation, Indian official notices, and open government datasets into explainable signal cards.

## What Makes This Version Real

This prototype does not depend on mock data or sponsor-only API access for its core demo. The current live pipeline refreshes from:

- Reddit public JSON listings plus targeted keyword search for diabetes, hypertension, asthma, and symptom-drug combinations.
- Google News RSS searches focused on India health-risk queries for rapid open-web corroboration.
- Curated YouTube public channel RSS feeds resolved from public handle pages for expert video explainers and community health coverage.
- Curated Telegram public channel mirrors for government-broadcast health and campaign updates available on open `/s/` pages.
- CDSCO homepage PDF notices filtered for drug quality, safety, biologics, vaccines, and medical device topics.
- National Health Mission updates filtered for NP-NCD, campaigns, MIS reports, and public-health program documents.
- data.gov.in RSS entries filtered for health and air-quality baseline datasets.

Official PDF notices are now text-extracted in the backend so NHM and CDSCO documents can contribute real searchable context instead of only link titles.

That source mix is the current unfair advantage: it gives the team a live end-to-end story without waiting for sponsor-only APIs or X credentials.

## Architecture

- Backend: FastAPI in [backend/app/main.py](backend/app/main.py)
- Source connectors: [backend/app/sources](backend/app/sources)
- Normalization and signal logic: [backend/app/pipeline.py](backend/app/pipeline.py)
- Frontend command center: [frontend/index.html](frontend/index.html), [frontend/app.js](frontend/app.js), [frontend/styles.css](frontend/styles.css)
- Cached live snapshots: [backend/data/latest_snapshot.json](backend/data/latest_snapshot.json)

## Local Run

From the backend folder:

```powershell
c:/Users/Imart/CopilotHacksAndPersonal/.venv/Scripts/python.exe -m pip install -r requirements.txt
c:/Users/Imart/CopilotHacksAndPersonal/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Open:

- API health: http://127.0.0.1:8011/health
- Live snapshot: http://127.0.0.1:8011/api/v1/snapshot?refresh=true
- Frontend: http://127.0.0.1:8011/app/

## API Surface

- `GET /health`: service health payload
- `GET /api/v1/snapshot`: current live multi-source snapshot
- `GET /api/v1/projects/defaults`: built-in project briefs
- `POST /api/v1/projects/analyze`: project-scoped filtered dashboard
- `GET /api/v1/research`: source strategy and differentiators for the UI

## Folder Map

- [backend](backend): FastAPI service, source connectors, tests, cached snapshots
- [frontend](frontend): static command-center UI served by FastAPI
- [docs/plan](docs/plan): requirements, design, and implementation task tracking

## Current Limitations

- MoHFW’s new site is not reliable for direct no-JS scraping, so it is documented but not in the live MVP connector path.
- Reddit remains useful but noisy, so it is treated as early evidence rather than proof.
- Official diabetes-specific notices may be sparse on any given day; the product therefore uses official sources more for context and corroboration than for volume.
- Public YouTube and Telegram ingestion depends on a curated allowlist, so coverage is intentionally selective rather than broad.
- Discord, OCR-heavy document extraction, and richer baseline connectors are still next-step integrations.

Project briefs also run an extra focused-search pass against Reddit and Google News, then dedupe and rerank that evidence separately from the broad shared snapshot.

## Next Build Targets

1. Expand curated YouTube and Telegram allowlists with more India-health channels once they are verified to expose stable public pages.
2. Add India-vs-world baseline panels from NFHS, GBD, and more data.gov.in datasets.
3. Expand synonym dictionaries for project briefs so more brand names and regional phrasing map to the same health concept.