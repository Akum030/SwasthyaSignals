# Requirements Document: SwasthyaSignals

## Introduction

SwasthyaSignals is a hackathon-stage but real-data social health early warning platform focused on Indian public-health and drug-safety use cases. The first milestone is not exhaustive coverage. It is a credible, end-to-end, explainable radar that works today using public sources that can actually be refreshed during the demo.

## Project Context

- Repository location: [Hackathons/SwasthyaSignals](../..)
- Frontend: static command-center UI served by FastAPI
- Backend: FastAPI with source-specific ingestion modules
- Target users: public-health analysts, hackathon judges, NGOs, journalists, and civic-tech teams
- Primary operating constraint: avoid dependence on paid or sponsor-only APIs for the live MVP

## Glossary

- Signal: a ranked alert card derived from multiple pieces of evidence
- Evidence item: one normalized source record such as a Reddit post, news item, or official notice
- Official context: Indian government or public institutional content used to anchor and validate social signals
- Baseline dataset: structured historical or indicator data that provides context rather than real-time chatter

## Requirements

### Requirement 1: Live Multi-Source Acquisition

**User Story:** As an analyst, I want the platform to refresh from real public sources so the dashboard is not a mockup.

#### Acceptance Criteria

1. WHEN the backend refreshes, THE system SHALL collect evidence from at least one public social source.
2. WHEN the backend refreshes, THE system SHALL collect evidence from at least one Indian official source.
3. WHEN the backend refreshes, THE system SHALL collect evidence from at least one public validation or baseline source.
4. THE system SHALL expose source health and item counts for every active connector.

### Requirement 2: India-First Health Relevance

**User Story:** As a reviewer, I want India-specific health relevance to be visible so the prototype is clearly not a generic global social listening tool.

#### Acceptance Criteria

1. WHEN items mention Indian regions or come from Indian official sources, THE system SHALL label them with India-oriented regional context.
2. THE system SHALL prioritize chronic disease, air quality, drug safety, and NP-NCD context.
3. THE system SHALL support project briefs that reflect Indian use cases such as diabetes drugs, hypertension, and pollution-linked asthma.

### Requirement 3: Explainable Signal Cards

**User Story:** As an analyst, I want every signal to show why it exists so I can trust or reject it quickly.

#### Acceptance Criteria

1. WHEN a signal is generated, THE system SHALL expose a title, summary, confidence score, tags, evidence count, and source overlap.
2. WHEN evidence links are available, THE system SHALL expose the original URLs.
3. THE system SHALL keep the ranking logic deterministic and explainable.

### Requirement 4: Privacy-Aware Normalization

**User Story:** As a builder, I want basic masking and normalization so the prototype does not display obvious personally identifying details.

#### Acceptance Criteria

1. THE system SHALL mask obvious email addresses and Indian phone numbers.
2. THE system SHALL normalize whitespace and detect coarse language classes.
3. THE system SHALL keep raw public URLs while redacting obvious personal contact data from copied text.

### Requirement 5: Project-Scoped Exploration

**User Story:** As a judge or analyst, I want to switch briefs quickly so I can see the same live evidence through different use-case lenses.

#### Acceptance Criteria

1. THE system SHALL provide built-in project presets.
2. THE system SHALL allow keyword-driven project setup from the UI.
3. WHEN a project is analyzed, THE system SHALL return filtered metrics, timeline, region split, signal cards, and evidence snippets.

### Requirement 6: Demo Credibility

**User Story:** As a hackathon team, I want the prototype to stand out because the acquisition strategy is clever and feasible, not because the UI is faked.

#### Acceptance Criteria

1. THE system SHALL document why each active source is used and what risk it carries.
2. THE system SHALL explicitly separate live MVP connectors from stretch connectors.
3. THE system SHALL avoid presenting unsupported platform coverage as already implemented.