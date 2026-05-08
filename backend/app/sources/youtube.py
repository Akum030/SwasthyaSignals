"""YouTube public channel RSS ingestion."""

from __future__ import annotations

from dataclasses import replace
import json
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree

from app.config import AppConfig
from app.html_utils import extract_meta_content, normalize_whitespace
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
CHANNEL_ID_PATTERN = re.compile(r'externalId":"([^"]+)"')
FEED_URL_PATTERN = re.compile(r'https://www.youtube.com/feeds/videos.xml\?channel_id=([^"&]+)')
SHORT_DESCRIPTION_PATTERN = re.compile(r'"shortDescription":"((?:\\.|[^\"])*)"')
INITIAL_DATA_PATTERN = re.compile(r"var ytInitialData = (\{.*?\});</script>", re.S)
WATCH_PAGE_DETAIL_THRESHOLD = 280


class YouTubeSource:
    """Collect recent videos from curated public YouTube channels."""

    name = "youtube"
    label = "YouTube public channel RSS"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch recent videos from configured public channel handles."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        errors: list[str] = []
        channel_count = max(1, len(config.youtube_channels))
        limit_per_channel = max(2, config.max_items_per_source // channel_count)

        for label, handle in config.youtube_channels:
            try:
                channel_id = _resolve_channel_id(handle, config)
                feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                xml_text = fetch_text(feed_url, config)
                parsed_items = _parse_feed_items(xml_text, label, seen_urls, limit_per_channel)
                items.extend(
                    _enrich_watch_page_items(parsed_items, config)
                )
            except SourceError as error:
                errors.append(str(error))

        if items or not errors:
            return items
        raise SourceError("; ".join(errors[:2]))

    def search_queries(self, queries: tuple[str, ...], config: AppConfig) -> list[ContentItem]:
        """Fetch query-focused YouTube search results for live project analysis."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        errors: list[str] = []
        query_count = max(1, len(queries))
        limit_per_query = max(2, config.max_items_per_source // query_count)

        for query in queries:
            try:
                html = fetch_text(
                    f"https://www.youtube.com/results?search_query={quote_plus(query)}",
                    config,
                )
                parsed_items = _parse_search_results(html, query, seen_urls, limit_per_query)
                items.extend(_enrich_watch_page_items(parsed_items, config))
            except SourceError as error:
                errors.append(str(error))

        if items or not errors:
            return items
        raise SourceError("; ".join(errors[:2]))


def _resolve_channel_id(handle: str, config: AppConfig) -> str:
    """Resolve a public YouTube handle into a channel ID for RSS access."""

    cleaned = handle.strip()
    if cleaned.startswith("UC"):
        return cleaned
    if not cleaned.startswith("@"):
        cleaned = f"@{cleaned}"

    html = fetch_text(f"https://www.youtube.com/{cleaned}/videos", config)
    match = CHANNEL_ID_PATTERN.search(html) or FEED_URL_PATTERN.search(html)
    if not match:
        raise SourceError(f"https://www.youtube.com/{cleaned}/videos -> channel id not found")
    return match.group(1)


def _parse_feed_items(
    xml_text: str,
    channel_label: str,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Parse a YouTube channel Atom feed into normalized items."""

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise SourceError("YouTube feed -> invalid XML payload") from error

    items: list[ContentItem] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = normalize_whitespace(entry.findtext("atom:title", default="", namespaces=ATOM_NS))
        link_node = entry.find("atom:link", ATOM_NS)
        url = normalize_whitespace(link_node.attrib.get("href", "") if link_node is not None else "")
        if not title or not url or url in seen_urls:
            continue
        seen_urls.add(url)
        description = normalize_whitespace(
            entry.findtext("media:group/media:description", default="", namespaces=ATOM_NS)
            or entry.findtext("atom:summary", default="", namespaces=ATOM_NS)
        )
        items.append(
            ContentItem(
                source="youtube",
                source_label=f"YouTube: {channel_label}",
                title=title,
                body=description or title,
                url=url,
                published_at=(
                    entry.findtext("atom:published", default=None, namespaces=ATOM_NS)
                    or entry.findtext("atom:updated", default=None, namespaces=ATOM_NS)
                ),
            )
        )
        if len(items) >= limit:
            break
    return items


def _enrich_watch_page_items(
    items: list[ContentItem],
    config: AppConfig,
) -> list[ContentItem]:
    """Fill thin YouTube feed snippets from the richer watch-page description."""

    enriched: list[ContentItem] = []
    for item in items:
        if len(item.body) >= WATCH_PAGE_DETAIL_THRESHOLD:
            enriched.append(item)
            continue
        try:
            html = fetch_text(item.url, config)
        except SourceError:
            enriched.append(item)
            continue

        page_description = _extract_watch_page_description(html)
        if page_description and len(page_description) > len(item.body):
            enriched.append(replace(item, body=page_description))
            continue
        enriched.append(item)
    return enriched


def _extract_watch_page_description(html: str) -> str:
    """Extract the most detailed YouTube watch-page description available."""

    match = SHORT_DESCRIPTION_PATTERN.search(html)
    if match:
        try:
            return normalize_whitespace(json.loads(f'"{match.group(1)}"'))
        except json.JSONDecodeError:
            pass

    return extract_meta_content(html, "og:description", "description")


def _parse_search_results(
    html: str,
    query: str,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Parse public YouTube search results into query-focused content items."""

    match = INITIAL_DATA_PATTERN.search(html)
    if not match:
        raise SourceError("YouTube search -> initial data not found")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise SourceError("YouTube search -> invalid initial data payload") from error

    items: list[ContentItem] = []
    for renderer in _iter_video_renderers(payload):
        video_id = renderer.get("videoId") or ""
        if not video_id:
            continue
        url = f"https://www.youtube.com/watch?v={video_id}"
        if url in seen_urls:
            continue
        title = _runs_text(renderer.get("title"))
        if not title:
            continue
        seen_urls.add(url)
        description = _runs_text(renderer.get("descriptionSnippet")) or _detailed_snippet_text(renderer)
        channel_label = _runs_text(renderer.get("ownerText")) or "YouTube Search"
        items.append(
            ContentItem(
                source="youtube",
                source_label=f"YouTube Search: {query} · {channel_label}",
                title=normalize_whitespace(title),
                body=normalize_whitespace(description or title),
                url=url,
                published_at=None,
            )
        )
        if len(items) >= limit:
            break
    return items


def _iter_video_renderers(node: object):
    """Yield nested videoRenderer nodes from YouTube initial data."""

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "videoRenderer" and isinstance(value, dict):
                yield value
                continue
            yield from _iter_video_renderers(value)
        return
    if isinstance(node, list):
        for value in node:
            yield from _iter_video_renderers(value)


def _runs_text(payload: object) -> str:
    """Flatten YouTube run-based text fragments into plain text."""

    if not isinstance(payload, dict):
        return ""
    simple_text = payload.get("simpleText")
    if isinstance(simple_text, str):
        return normalize_whitespace(simple_text)
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return ""
    return normalize_whitespace(" ".join(run.get("text", "") for run in runs if isinstance(run, dict)))


def _detailed_snippet_text(renderer: dict[str, object]) -> str:
    """Extract longer snippet text from detailed search metadata when present."""

    snippets = renderer.get("detailedMetadataSnippets")
    if not isinstance(snippets, list):
        return ""
    parts: list[str] = []
    for snippet in snippets:
        if not isinstance(snippet, dict):
            continue
        snippet_text = _runs_text(snippet.get("snippetText"))
        if snippet_text:
            parts.append(snippet_text)
    return normalize_whitespace(" ".join(parts))