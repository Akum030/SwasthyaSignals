"""Normalization, enrichment, and signal generation logic."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from html import unescape
import re

from app.config import (
    ENTITY_LEXICONS,
    HEALTH_CONTEXT_KEYWORDS,
    INDIA_REGIONS,
    NEGATIVE_CUES,
    OFFICIAL_KEYWORDS,
    POSITIVE_CUES,
    PROJECT_SYNONYMS,
)
from app.models import ContentItem, SignalCard


EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
MARKDOWN_ESCAPE_PATTERN = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>~|])")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((?:https?://)?[^\s)]+\)")
MARKDOWN_HEADER_PATTERN = re.compile(r"(?m)^\s{0,3}(?:#{1,6}|>+)\s*")
MARKDOWN_LIST_PATTERN = re.compile(r"(?m)^\s{0,3}(?:[-*+]|\d+\.)\s+")
MARKDOWN_RULE_PATTERN = re.compile(r"(?m)^\s*[-*_]{3,}\s*$")
MARKDOWN_TABLE_DIVIDER_PATTERN = re.compile(r"(?m)^\s*\|?(?:\s*:?-+:?\s*\|)+\s*$")
MARKDOWN_FORMATTING_PATTERN = re.compile(r"\*\*|__|~~|`+")
FOCUS_SIGNAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "effect",
    "effects",
    "for",
    "in",
    "india",
    "india-first",
    "of",
    "on",
    "or",
    "side",
    "the",
    "vs",
    "with",
    "world",
}


def _build_entity_canonical_map() -> dict[str, str]:
    """Map known alias variants back to the canonical term used in summaries."""

    mapping: dict[str, str] = {}
    for phrases in ENTITY_LEXICONS.values():
        for phrase in phrases:
            mapping[phrase] = phrase

    for canonical, synonyms in PROJECT_SYNONYMS.items():
        if canonical not in mapping:
            continue
        for synonym in synonyms:
            if synonym in mapping:
                mapping[synonym] = canonical
    return mapping


ENTITY_CANONICAL_MAP = _build_entity_canonical_map()
ENTITY_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    category: [
        (
            phrase,
            re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)"),
        )
        for phrase in phrases
    ]
    for category, phrases in ENTITY_LEXICONS.items()
}


def strip_markup(text: str) -> str:
    """Flatten common lightweight markdown and escaped formatting to plain text."""

    cleaned = unescape(text or "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = MARKDOWN_ESCAPE_PATTERN.sub(r"\1", cleaned)
    cleaned = MARKDOWN_LINK_PATTERN.sub(r"\1", cleaned)
    cleaned = MARKDOWN_TABLE_DIVIDER_PATTERN.sub(" ", cleaned)
    cleaned = MARKDOWN_RULE_PATTERN.sub(" ", cleaned)
    cleaned = MARKDOWN_HEADER_PATTERN.sub("", cleaned)
    cleaned = MARKDOWN_LIST_PATTERN.sub("", cleaned)
    cleaned = cleaned.replace("|", " ")
    cleaned = MARKDOWN_FORMATTING_PATTERN.sub("", cleaned)
    return cleaned


def normalize_text(text: str) -> str:
    """Normalize whitespace in arbitrary source text."""

    return " ".join(strip_markup(text).split())


def mask_pii(text: str) -> str:
    """Mask obvious email and Indian phone number patterns."""

    masked = EMAIL_PATTERN.sub("[email]", text)
    masked = PHONE_PATTERN.sub("[phone]", masked)
    return masked


def detect_language(text: str) -> str:
    """Use a lightweight heuristic for language classification."""

    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract keyword-matched entities from normalized text."""

    lowered = text.lower()
    entities: dict[str, list[str]] = {}
    for category, phrase_patterns in ENTITY_PATTERNS.items():
        matches = [
            ENTITY_CANONICAL_MAP.get(phrase, phrase)
            for phrase, pattern in phrase_patterns
            if pattern.search(lowered)
        ]
        if matches:
            entities[category] = sorted(set(matches))
    return entities


def infer_region(text: str, official: bool) -> str:
    """Infer an India-centric region label from mentions in text."""

    lowered = text.lower()
    for region in INDIA_REGIONS:
        if region in lowered:
            return region.title()
    if official:
        return "India"
    return "Global"


def score_sentiment(text: str) -> str:
    """Assign a coarse sentiment label using domain cues."""

    lowered = text.lower()
    negative_hits = sum(1 for cue in NEGATIVE_CUES if cue in lowered)
    positive_hits = sum(1 for cue in POSITIVE_CUES if cue in lowered)
    if negative_hits > positive_hits:
        return "negative"
    if positive_hits > negative_hits:
        return "positive"
    return "neutral"


def classify_tags(text: str, entities: dict[str, list[str]], official: bool) -> list[str]:
    """Derive lightweight classification tags from text and entity matches."""

    tags: list[str] = []
    lowered = text.lower()
    if official:
        tags.append("official")
    if "drugs" in entities and "symptoms" in entities:
        tags.append("ADR-like")
    if "lifestyle" in entities:
        tags.append("Lifestyle")
    if any(keyword in lowered for keyword in ("quality", "recall", "alert")):
        tags.append("Safety")
    if any(keyword in lowered for keyword in ("guideline", "advisory", "notice")):
        tags.append("Policy")
    return sorted(set(tags))


def is_adr_like(text: str, entities: dict[str, list[str]]) -> bool:
    """Identify likely adverse-event chatter with simple rules."""

    lowered = text.lower()
    if "drugs" in entities and "symptoms" in entities:
        return True
    return any(phrase in lowered for phrase in ("side effect", "adverse", "reaction"))


def enrich_item(item: ContentItem) -> ContentItem:
    """Normalize and enrich a content item in one pass."""

    cleaned_body = mask_pii(normalize_text(item.body))
    cleaned_title = normalize_text(item.title)
    merged = " ".join(part for part in (cleaned_title, cleaned_body) if part)
    entities = extract_entities(merged)
    tags = classify_tags(merged, entities, item.official)
    return replace(
        item,
        title=cleaned_title,
        body=cleaned_body,
        language=detect_language(merged),
        sentiment=score_sentiment(merged),
        adr_like=is_adr_like(merged, entities),
        entities=entities,
        tags=tags,
        region=infer_region(merged, item.official),
    )


def filter_relevant_items(items: list[ContentItem]) -> list[ContentItem]:
    """Drop official links that do not contain enough health signal."""

    relevant: list[ContentItem] = []
    for item in items:
        merged = item.merged_text().lower()
        has_signal = bool(item.entities) or any(keyword in merged for keyword in OFFICIAL_KEYWORDS)
        has_core_entities = bool(
            item.entities.get("drugs")
            or item.entities.get("conditions")
            or item.entities.get("symptoms")
        )
        has_health_context = has_core_entities or any(keyword in merged for keyword in HEALTH_CONTEXT_KEYWORDS)
        if item.source in {"reddit", "google_news", "youtube", "telegram"}:
            if has_signal and has_health_context:
                relevant.append(item)
            continue
        if has_signal:
            relevant.append(item)
    return relevant


def build_signals(items: list[ContentItem]) -> list[SignalCard]:
    """Group evidence into explainable signal cards."""

    grouped: dict[tuple[str, str], list[ContentItem]] = defaultdict(list)

    for item in items:
        conditions = item.entities.get("conditions", [])
        drugs = item.entities.get("drugs", [])
        symptoms = item.entities.get("symptoms", [])
        lifestyle = item.entities.get("lifestyle", [])

        primary = drugs[:1] or conditions[:1] or symptoms[:1] or lifestyle[:1]
        secondary = symptoms[:1] or conditions[1:2] or lifestyle[1:2]
        if primary:
            if primary[0] in symptoms:
                secondary = conditions[:1] or lifestyle[:1]
            key = (
                _canonicalize_signal_term(primary[0]),
                _canonicalize_signal_term(secondary[0]) if secondary else "general",
            )
        elif item.official:
            key = (item.title.lower()[:40], "official")
        else:
            fallback_key = _fallback_signal_key(item)
            if fallback_key is None:
                continue
            key = fallback_key
        grouped[key].append(item)

    signals: list[SignalCard] = []
    for (primary, secondary), evidence in grouped.items():
        source_names = sorted({item.source for item in evidence})
        official_refs = [item.url for item in evidence if item.official][:3]
        tags = sorted({tag for item in evidence for tag in item.tags})
        evidence_count = len(evidence)
        negative_count = sum(item.sentiment == "negative" for item in evidence)
        adr_count = sum(item.adr_like for item in evidence)
        official_only = all(item.official for item in evidence)
        confidence = min(
            98,
            25
            + len(source_names) * 18
            + len(official_refs) * 12
            + adr_count * 8
            + negative_count * 5
            + evidence_count * 3,
        )
        region = evidence[0].region
        if official_only:
            title = f"Official advisory: {evidence[0].title}"
            if len(title) > 96:
                title = f"{title[:93].rstrip()}..."
            summary = (
                f"{evidence_count} official reference(s) from "
                f"{', '.join(source_names)} indicate a fresh policy, safety, "
                f"or guidance movement."
            )
        elif secondary == "general":
            title = f"{primary.title()} concern cluster"
            summary = (
                f"{evidence_count} recent items mention {primary} across "
                f"{len(source_names)} sources."
            )
        else:
            title = f"{primary.title()} + {secondary.title()} signal"
            summary = (
                f"{evidence_count} recent items connect {primary} with "
                f"{secondary} across {len(source_names)} sources."
            )
        signals.append(
            SignalCard(
                title=title,
                summary=summary,
                confidence=confidence,
                tags=tags,
                evidence_count=evidence_count,
                sources=source_names,
                official_references=official_refs,
                example_urls=[item.url for item in evidence[:3]],
                region=region,
            )
        )

    signals.sort(key=lambda card: (-card.confidence, -card.evidence_count, card.title))
    return signals[:8]


def _canonicalize_signal_term(term: str) -> str:
    """Normalize a signal term so alias variants collapse into one card."""

    cleaned = " ".join(term.lower().strip().split())
    return ENTITY_CANONICAL_MAP.get(cleaned, cleaned)


def _fallback_signal_key(item: ContentItem) -> tuple[str, str] | None:
    """Build a signal key from a focused search label when entity extraction is too sparse."""

    phrase = _extract_focus_signal_phrase(item.source_label)
    if not phrase:
        return None
    return (_canonicalize_signal_term(phrase), "general")


def _extract_focus_signal_phrase(source_label: str) -> str | None:
    """Recover the meaningful part of a focused search label for signal fallback."""

    lowered = source_label.lower().strip()
    if lowered.startswith("search:"):
        raw_query = lowered.split("search:", maxsplit=1)[1]
    elif lowered.startswith("google news"):
        raw_query = lowered.split(":", maxsplit=1)[1]
    else:
        return None

    raw_query = raw_query.split("·", maxsplit=1)[0]

    terms: list[str] = []
    for part in re.split(r"\s+", raw_query):
        cleaned = re.sub(r"[^a-z0-9+-]", "", part)
        if len(cleaned) < 3 or cleaned in FOCUS_SIGNAL_STOPWORDS:
            continue
        terms.append(cleaned)
    if not terms:
        return None
    return " ".join(terms[:4])


def summarize_topics(items: list[ContentItem]) -> list[dict[str, object]]:
    """Produce high-level topic counts for dashboard tiles."""

    counts: dict[str, int] = defaultdict(int)
    for item in items:
        for category in ("conditions", "drugs", "lifestyle"):
            for entity in item.entities.get(category, [])[:2]:
                counts[entity] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"topic": name, "count": count} for name, count in ranked[:10]]


def utc_now_iso() -> str:
    """Return the current UTC time in ISO format."""

    return datetime.now(tz=timezone.utc).isoformat()
