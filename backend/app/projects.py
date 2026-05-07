"""Project presets and project-scoped dashboard shaping helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
import re

from app.config import AppConfig, ENTITY_LEXICONS, HEALTH_CONTEXT_KEYWORDS, PROJECT_SYNONYMS
from app.pipeline import build_signals, enrich_item, summarize_topics
from app.sources.base import SourceError
from app.sources.google_news import GoogleNewsSource
from app.sources.reddit import RedditSource


OFFICIAL_CONTEXT_KEYWORDS = (
    "ncd",
    "guideline",
    "guidelines",
    "quality",
    "complaint",
    "safety",
    "drug",
    "medical device",
    "campaign",
    "mental health",
    "anemia",
    "anaemia",
    "tuberculosis",
    "air quality",
    "pollution",
)

OFFICIAL_CONTEXT_BRIDGE_MAP: dict[str, tuple[str, ...]] = {
    "diabetes": ("diabetes", "blood sugar", "ncd", "non-communicable"),
    "metformin": ("diabetes", "blood sugar", "ncd", "non-communicable"),
    "insulin": ("diabetes", "blood sugar", "ncd", "non-communicable"),
    "semaglutide": ("diabetes", "obesity", "ncd", "non-communicable"),
    "tirzepatide": ("diabetes", "obesity", "ncd", "non-communicable"),
    "blood sugar": ("diabetes", "blood sugar", "ncd", "non-communicable"),
    "hypertension": ("hypertension", "blood pressure", "ncd", "non-communicable"),
    "blood pressure": ("hypertension", "blood pressure", "ncd", "non-communicable"),
    "obesity": ("obesity", "ncd", "non-communicable"),
    "asthma": ("asthma", "respiratory", "ncd", "non-communicable"),
    "tuberculosis": ("tuberculosis", "tb", "programme"),
    "tb": ("tuberculosis", "tb", "programme"),
}

HEALTH_SUBREDDIT_TOKENS = (
    "askdocs",
    "asthma",
    "chronic",
    "cfs",
    "diabetes",
    "eczema",
    "glp",
    "hashimoto",
    "health",
    "hypertension",
    "medical",
    "mounjaro",
    "obesity",
    "pcos",
    "prediabetes",
    "semaglutide",
    "t1d",
    "t2d",
)

FOCUS_QUERY_STOPWORDS = {
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


DEFAULT_PROJECTS: list[dict[str, object]] = [
    {
        "name": "Diabetes drugs - India vs World",
        "description": (
            "Watch drug safety chatter, cardiometabolic lifestyle risk, and "
            "official diabetes-related references."
        ),
        "keywords": [
            "diabetes",
            "insulin",
            "metformin",
            "semaglutide",
            "mounjaro",
            "blood sugar",
        ],
        "sources": ["reddit", "google_news", "youtube", "telegram", "cdsco", "nhm", "data_gov"],
        "latency_profile": "Realtime",
    },
    {
        "name": "Air pollution and asthma - NCR",
        "description": (
            "Track pollution-linked respiratory complaints with Indian official context."
        ),
        "keywords": ["pollution", "asthma", "wheezing", "cough", "delhi", "ncr"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm", "data_gov"],
        "latency_profile": "Daily",
    },
    {
        "name": "Childhood diabetes policy watch",
        "description": (
            "Look for children-focused diabetes discussion, guidelines, and access signals."
        ),
        "keywords": ["child", "children", "diabetes", "guidelines", "school"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "cdsco", "nhm", "data_gov"],
        "latency_profile": "Daily",
    },
    {
        "name": "Hypertension medicine safety watch",
        "description": (
            "Track blood-pressure medication complaints, dizziness, palpitations, "
            "and Indian safety context."
        ),
        "keywords": ["hypertension", "blood pressure", "amlodipine", "telmisartan", "dizziness", "palpitations"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "cdsco", "nhm"],
        "latency_profile": "Daily",
    },
    {
        "name": "Obesity injectables and GI side effects",
        "description": (
            "Follow nausea, vomiting, appetite, and adherence chatter around GLP-1 and dual-agonist drugs."
        ),
        "keywords": ["obesity", "semaglutide", "tirzepatide", "mounjaro", "ozempic", "nausea"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "cdsco", "nhm"],
        "latency_profile": "Realtime",
    },
    {
        "name": "Fatty liver and metabolic risk - India",
        "description": (
            "Monitor NAFLD-style chatter, diet risk, diabetes overlap, and liver-health explainers."
        ),
        "keywords": ["fatty liver", "nafld", "liver", "diabetes", "obesity", "diet"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm", "data_gov"],
        "latency_profile": "Daily",
    },
    {
        "name": "TB medicine adherence and cough watch",
        "description": (
            "Track tuberculosis symptoms, medicine adherence challenges, and Indian program references."
        ),
        "keywords": ["tuberculosis", "tb", "cough", "breathlessness", "medicine", "adherence"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm", "data_gov"],
        "latency_profile": "Daily",
    },
    {
        "name": "Thyroid fatigue and weight fluctuation watch",
        "description": (
            "Look for thyroid-linked fatigue, palpitations, brain fog, and weight-change narratives."
        ),
        "keywords": ["thyroid", "fatigue", "weight gain", "palpitations", "brain fog"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm"],
        "latency_profile": "Daily",
    },
    {
        "name": "PCOS and insulin resistance watch",
        "description": (
            "Track PCOS symptoms, cycle disruption, insulin resistance chatter, and treatment discussions."
        ),
        "keywords": ["pcos", "insulin resistance", "metformin", "weight gain", "period"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm"],
        "latency_profile": "Realtime",
    },
    {
        "name": "Dengue fever and platelet watch",
        "description": (
            "Follow dengue symptom spikes, fever chatter, platelet concerns, and local public-health updates."
        ),
        "keywords": ["dengue", "fever", "platelet", "rash", "headache"],
        "sources": ["reddit", "google_news", "youtube", "telegram", "nhm", "data_gov"],
        "latency_profile": "Realtime",
    },
]


def build_project_view(
    snapshot: dict[str, object],
    project: dict[str, object],
    focus_items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Filter a snapshot into a project-scoped response for the frontend."""

    keywords = [keyword.lower().strip() for keyword in project.get("keywords", []) if keyword.strip()]
    expanded_keywords = _expand_project_keywords(keywords)
    allowed_sources = {source.lower() for source in project.get("sources", []) if source}
    include_official_only = bool(project.get("include_official_only", False))

    filtered_items: list[dict[str, object]] = []
    official_context: list[dict[str, object]] = []
    focus_queries = _build_focus_queries(expanded_keywords)
    seen_urls: set[str] = set()
    for item in snapshot.get("items", []):
        merged = f"{item['title']} {item['body']}".lower()
        if allowed_sources and item["source"] not in allowed_sources:
            continue
        official_matches_brief = _official_context_matches_brief(merged, expanded_keywords)
        if item["official"] and official_matches_brief and any(keyword in merged for keyword in OFFICIAL_CONTEXT_KEYWORDS):
            official_context.append(item)
        if include_official_only and not item["official"]:
            continue
        if expanded_keywords and _count_keyword_hits(merged, expanded_keywords) == 0:
            continue
        if expanded_keywords and not _passes_project_relevance(item, expanded_keywords):
            continue
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        filtered_items.append(item)

    live_focus_items = focus_items if focus_items is not None else _collect_project_focus_items(project, allowed_sources)
    for item in live_focus_items:
        merged = f"{item['title']} {item['body']}".lower()
        if allowed_sources and item["source"] not in allowed_sources:
            continue
        if include_official_only and not item["official"]:
            continue
        if expanded_keywords and _count_keyword_hits(merged, expanded_keywords) == 0:
            continue
        if expanded_keywords and not _passes_project_relevance(item, expanded_keywords):
            continue
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        filtered_items.append(item)

    for item in official_context:
        if item in filtered_items:
            continue
        filtered_items.append(item)
        if len([entry for entry in filtered_items if entry["official"]]) >= 3:
            break

    filtered_items.sort(
        key=lambda item: (_item_relevance_score(item, expanded_keywords), item.get("published_at") or ""),
        reverse=True,
    )

    signals = build_signals([
        _dict_to_content_item(item) for item in filtered_items
    ])
    timeline = _build_timeline(filtered_items)
    region_counts = Counter(item["region"] for item in filtered_items)
    source_counts = Counter(item["source"] for item in filtered_items)
    india_count = sum(1 for item in filtered_items if item["region"] != "Global")
    global_count = sum(1 for item in filtered_items if item["region"] == "Global")
    official_count = sum(1 for item in filtered_items if item["official"])

    return {
        "project": project,
        "generated_at": snapshot.get("generated_at"),
        "source_status": snapshot.get("source_status", []),
        "focus_queries": focus_queries,
        "metrics": {
            "item_count": len(filtered_items),
            "signal_count": len(signals),
            "india_count": india_count,
            "global_count": global_count,
            "official_count": official_count,
            "social_count": max(0, len(filtered_items) - official_count),
        },
        "timeline": timeline,
        "source_breakdown": [
            {"source": source, "count": count}
            for source, count in source_counts.most_common()
        ],
        "region_breakdown": [
            {"region": region, "count": count}
            for region, count in region_counts.most_common()
        ],
        "topics": summarize_topics([
            _dict_to_content_item(item) for item in filtered_items
        ]),
        "signals": [signal.to_dict() for signal in signals],
        "items": filtered_items[:40],
    }


def _collect_project_focus_items(
    project: dict[str, object],
    allowed_sources: set[str],
) -> list[dict[str, object]]:
    """Fetch a small amount of project-specific live search evidence."""

    keywords = [keyword.lower().strip() for keyword in project.get("keywords", []) if keyword.strip()]
    if not keywords:
        return []

    queries = _build_focus_queries(_expand_project_keywords(keywords))
    if not queries:
        return []

    focused_config = replace(
        AppConfig(),
        max_items_per_source=12,
        reddit_subreddits=tuple(),
        reddit_search_queries=tuple(queries),
        news_search_queries=tuple(queries),
    )

    items: list[dict[str, object]] = []
    source_specs = [
        ("reddit", RedditSource()),
        ("google_news", GoogleNewsSource()),
    ]
    for source_name, source in source_specs:
        if allowed_sources and source_name not in allowed_sources:
            continue
        try:
            fetched_items = source.fetch(focused_config)
        except SourceError:
            continue
        items.extend(enrich_item(item).to_dict() for item in fetched_items)
    return items


def _build_focus_queries(keywords: list[str]) -> list[str]:
    """Build a compact set of search queries from the active project keywords."""

    cleaned_keywords: list[str] = []
    for keyword in keywords:
        cleaned = " ".join(part for part in keyword.split() if part not in {"vs", "and", "or"})
        if cleaned and cleaned not in cleaned_keywords:
            cleaned_keywords.append(cleaned)

    if not cleaned_keywords:
        return []

    drug_terms = set(ENTITY_LEXICONS.get("drugs", ()))
    queries: list[str] = []
    is_narrow_brief = 1 < len(cleaned_keywords) <= 3
    if len(cleaned_keywords) >= 2:
        queries.append(f"india {cleaned_keywords[0]} {cleaned_keywords[1]}")
    for keyword in cleaned_keywords[:4]:
        if not is_narrow_brief:
            queries.append(f"india {keyword}")
        if keyword in drug_terms:
            queries.append(f"{keyword} side effect")

    deduped: list[str] = []
    for query in queries:
        if query not in deduped:
            deduped.append(query)
    return deduped[:6]


def _item_relevance_score(item: dict[str, object], keywords: list[str]) -> int:
    """Rank project evidence so the most relevant live items surface first."""

    merged = f"{item['title']} {item['body']}".lower()
    score = _count_keyword_hits(merged, keywords) * 10
    if item.get("official"):
        score += 8
    if item.get("adr_like"):
        score += 5
    source_label = str(item.get("source_label", ""))
    if source_label.startswith("search:") or source_label.startswith("Google News RSS:"):
        score += 4
    return score


def _passes_project_relevance(item: dict[str, object], keywords: list[str]) -> bool:
    """Require health context in addition to keyword overlap for project evidence."""

    if item.get("official"):
        return True

    title = str(item.get("title", "")).lower()
    body = str(item.get("body", "")).lower()
    merged = f"{title} {body}".strip()
    keyword_hits = _count_keyword_hits(merged, keywords)
    entities = item.get("entities", {}) or {}
    has_core_entities = bool(
        entities.get("drugs")
        or entities.get("conditions")
        or entities.get("symptoms")
    )
    has_health_context = has_core_entities or any(keyword in merged for keyword in HEALTH_CONTEXT_KEYWORDS)
    source_label = str(item.get("source_label", ""))
    focus_query_terms = _extract_focus_query_terms(source_label)
    if focus_query_terms:
        focus_query_hits = _count_keyword_hits(merged, focus_query_terms)
        required_focus_hits = 2 if len(focus_query_terms) >= 2 else 1
        if focus_query_hits < required_focus_hits:
            return False
        if required_focus_hits >= 2:
            title_hits = _count_keyword_hits(title, focus_query_terms)
            if title_hits == 0 and not _has_sentence_level_focus_alignment(body, focus_query_terms, required_focus_hits):
                return False
    if item.get("source") == "reddit" and source_label.startswith("search:"):
        if not _reddit_item_is_health_adjacent(item) and keyword_hits < 3:
            return False
    if item.get("adr_like") and has_health_context:
        return True
    if keyword_hits >= 2 and has_health_context:
        return True
    if keyword_hits >= 1 and has_core_entities:
        return True
    return False


def _reddit_item_is_health_adjacent(item: dict[str, object]) -> bool:
    """Check whether a Reddit result comes from a health-adjacent subreddit."""

    url = str(item.get("url", "")).lower()
    match = re.search(r"/r/([^/]+)/", url)
    if not match:
        return False
    subreddit = match.group(1)
    return any(token in subreddit for token in HEALTH_SUBREDDIT_TOKENS)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count distinct keyword phrases present in text using word boundaries."""

    hits = 0
    for keyword in keywords:
        cleaned = keyword.strip().lower()
        if not cleaned:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(cleaned)}(?!\w)")
        if pattern.search(text):
            hits += 1
    return hits


def _official_context_matches_brief(text: str, keywords: list[str]) -> bool:
    """Allow direct keyword matches plus a narrow family of official health-programme bridge terms."""

    if not keywords:
        return True
    if _count_keyword_hits(text, keywords) > 0:
        return True

    bridge_terms: list[str] = []
    for keyword in keywords:
      for term in OFFICIAL_CONTEXT_BRIDGE_MAP.get(keyword, ()):  # noqa: PLW2901
          if term not in bridge_terms:
              bridge_terms.append(term)
    return bool(bridge_terms) and _count_keyword_hits(text, bridge_terms) > 0


def _extract_focus_query_terms(source_label: str) -> list[str]:
    """Extract meaningful terms from a focused search label for stricter matching."""

    lowered = source_label.lower().strip()
    if lowered.startswith("search:"):
        raw_query = lowered.split("search:", maxsplit=1)[1]
    elif lowered.startswith("google news rss:"):
        raw_query = lowered.split(":", maxsplit=1)[1]
    else:
        return []

    terms: list[str] = []
    for part in re.split(r"\s+", raw_query):
        cleaned = re.sub(r"[^a-z0-9+-]", "", part)
        if len(cleaned) < 3 or cleaned in FOCUS_QUERY_STOPWORDS:
            continue
        if cleaned not in terms:
            terms.append(cleaned)
    return terms


def _expand_project_keywords(keywords: list[str]) -> list[str]:
    """Expand canonical project keywords with a compact synonym/brand alias family."""

    expanded: list[str] = []
    family_map = _project_keyword_family_map()
    for keyword in keywords:
        cleaned = keyword.strip().lower()
        if not cleaned:
            continue
        family = family_map.get(cleaned, (cleaned,))
        for term in family:
            if term not in expanded:
                expanded.append(term)
    return expanded


def _project_keyword_family_map() -> dict[str, tuple[str, ...]]:
    """Build a reverse index so canonical terms and aliases expand to the same family."""

    family_map: dict[str, tuple[str, ...]] = {}
    for canonical, synonyms in PROJECT_SYNONYMS.items():
        family = tuple(dict.fromkeys((canonical, *synonyms)))
        for term in family:
            family_map[term] = family
    return family_map


def _has_sentence_level_focus_alignment(text: str, keywords: list[str], required_hits: int) -> bool:
    """Require focused query terms to co-occur within the same sentence-sized chunk."""

    for sentence in re.split(r"[.!?;:\n]+", text):
        if _count_keyword_hits(sentence, keywords) >= required_hits:
            return True
    return False


def _build_timeline(items: list[dict[str, object]]) -> list[dict[str, object]]:
    """Aggregate recent items into a simple daily timeline."""

    counts: dict[str, int] = defaultdict(int)
    for item in items:
        published = item.get("published_at") or "unknown"
        day = published[:10] if published != "unknown" else "unknown"
        counts[day] += 1
    return [
        {"day": day, "count": counts[day]}
        for day in sorted(counts)
    ]


def _dict_to_content_item(item: dict[str, object]):
    """Lazily convert API dicts back into ContentItem objects."""

    from app.models import ContentItem

    return ContentItem(
        source=item["source"],
        source_label=item["source_label"],
        title=item["title"],
        body=item["body"],
        url=item["url"],
        published_at=item["published_at"],
        region=item["region"],
        official=item["official"],
        language=item["language"],
        sentiment=item["sentiment"],
        adr_like=item["adr_like"],
        entities=item["entities"],
        tags=item["tags"],
    )
