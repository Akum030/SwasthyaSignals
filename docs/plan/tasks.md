# Implementation Plan: SwasthyaSignals

## Overview

This task list tracks the real-data MVP, not the long-term product. The current goal is a defensible hackathon prototype that refreshes live, tells a strong India-first story, and is explainable end to end.

## Tasks

- [x] 1. Recover the existing project shell
  - [x] 1.1 Verify backend and frontend structure already in the folder
  - [x] 1.2 Confirm the previous startup issue was pathing and port-related rather than broken code

- [x] 2. Establish a live no-key source mesh
  - [x] 2.1 Keep Reddit as the primary public social source
  - [x] 2.2 Add Google News RSS as open-web corroboration
  - [x] 2.3 Tighten CDSCO notice scraping around safety and quality themes
  - [x] 2.4 Tighten NHM scraping around NP-NCD and public-health program documents
  - [x] 2.5 Add data.gov.in as a live baseline context source

- [x] 3. Improve source relevance and pipeline quality
  - [x] 3.1 Add stronger relevance gates for social evidence
  - [x] 3.2 Reduce Reddit over-weighting with smaller per-bucket limits
  - [x] 3.3 Remove overly generic entity matches that create false signal cards

- [x] 4. Document the research and architecture
  - [x] 4.1 Add requirements document
  - [x] 4.2 Add design document with acquisition strategy
  - [x] 4.3 Add README for local run and demo framing

- [x] 5. Sharpen the command-center UI
  - [x] 5.1 Surface the live source mix more clearly in the frontend
  - [x] 5.2 Show refresh timing and acquisition credibility in the UI

- [x] 6. Validate the end-to-end prototype
  - [x] 6.1 Restart the backend with the latest code
  - [x] 6.2 Save a fresh live snapshot to disk
  - [x] 6.3 Run the backend tests
  - [x] 6.4 Verify the frontend route and API responses together

- [ ] 7. Phase-two depth after MVP stabilization
  - [x] 7.1 Add PDF text extraction for official notices
  - [x] 7.2 Add curated YouTube and Telegram connectors
  - [ ] 7.3 Add NFHS and GBD baseline ingestion
  - [x] 7.4 Add project-aware ingestion strategies and synonym expansion
    - Focused Reddit and Google News query augmentation is implemented
    - Initial synonym expansion is implemented for compact brand and alias matching