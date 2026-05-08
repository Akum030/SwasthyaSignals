"""Google News ingestion for public health validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree

from app.config import AppConfig
from app.html_utils import normalize_whitespace, resolve_url, strip_tags
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


class GoogleNewsSource:
    """Collect India-focused health stories from Google News."""

    name = "google_news"
    label = "Google News"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch a small, query-focused set of public news entries."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        query_count = max(1, len(config.news_search_queries))
        limit_per_query = max(2, config.max_items_per_source // query_count)

        for query in config.news_search_queries:
            html_items = _fetch_search_result_items(query, config, seen_urls, limit_per_query)
            if html_items:
                items.extend(html_items)
                continue

            items.extend(_fetch_rss_items(query, config, self.label, seen_urls, limit_per_query))

        return items


class _SearchResultCollector(HTMLParser):
    """Collect visible Google News result anchors with their aria-label metadata."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str, str]] = []
        self._current_href: str | None = None
        self._current_aria_label: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track candidate result anchors."""

        if tag != "a":
            return
        attributes = dict(attrs)
        href = normalize_whitespace(attributes.get("href") or "")
        aria_label = normalize_whitespace(attributes.get("aria-label") or "")
        if not href or not aria_label:
            return
        if "/read/" not in href and "/articles/" not in href:
            return
        self._current_href = href
        self._current_aria_label = aria_label
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        """Buffer text inside the current anchor."""

        if self._current_href is None:
            return
        self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finalize the current anchor when it closes."""

        if tag != "a" or self._current_href is None or self._current_aria_label is None:
            return
        title = normalize_whitespace(" ".join(self._text_parts))
        if title:
            self.results.append((self._current_href, title, self._current_aria_label))
        self._current_href = None
        self._current_aria_label = None
        self._text_parts = []


def _fetch_search_result_items(
    query: str,
    config: AppConfig,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Fetch query-focused Google News search cards from the HTML results page."""

    url = (
        "https://news.google.com/search"
        f"?q={quote_plus(f'{query} when:30d')}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    html = fetch_text(url, config)
    return _parse_search_result_items(html, query, seen_urls, limit)


def _parse_search_result_items(
    html: str,
    query: str,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Parse visible Google News search result cards into normalized items."""

    parser = _SearchResultCollector()
    parser.feed(html)

    items: list[ContentItem] = []
    for href, title, aria_label in parser.results:
        link = resolve_url("https://news.google.com/", href)
        if not title or not link or link in seen_urls:
            continue
        publisher_name, date_text, author_name = _search_result_metadata(title, aria_label)
        seen_urls.add(link)
        items.append(
            ContentItem(
                source="google_news",
                source_label=_source_label("Google News Search", query, publisher_name),
                title=title,
                body=_search_result_body(title, publisher_name, date_text, author_name),
                url=link,
                published_at=_parse_result_date(date_text),
            )
        )
        if len(items) >= limit:
            break

    return items


def _fetch_rss_items(
    query: str,
    config: AppConfig,
    label: str,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Fall back to the RSS feed when HTML search parsing yields nothing."""

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(f'{query} when:30d')}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    xml_text = fetch_text(url, config)
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise SourceError(f"{url} -> invalid RSS payload") from error

    items: list[ContentItem] = []
    for node in root.findall(".//item"):
        title = normalize_whitespace((node.findtext("title") or "").replace(" - Google News", ""))
        link = normalize_whitespace(node.findtext("link") or "")
        if not title or not link or link in seen_urls:
            continue
        publisher_name, _publisher_url = _source_metadata(node.find("source"))
        seen_urls.add(link)
        items.append(
            ContentItem(
                source="google_news",
                source_label=_source_label(label, query, publisher_name),
                title=title,
                body=_item_body(title, node.findtext("description"), publisher_name),
                url=link,
                published_at=_parse_pub_date(node.findtext("pubDate")),
            )
        )
        if len(items) >= limit:
            break

    return items


def _parse_pub_date(raw_value: str | None) -> str | None:
    """Convert an RSS pubDate into ISO-8601 when possible."""

    if not raw_value:
        return None
    try:
        return parsedate_to_datetime(raw_value).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


def _parse_result_date(raw_value: str | None) -> str | None:
    """Convert a Google News search-card date fragment into ISO-8601 when possible."""

    if not raw_value:
        return None

    cleaned = normalize_whitespace(raw_value)
    now = datetime.now(timezone.utc)
    relative_match = re.fullmatch(r"(\d+)\s+(minute|minutes|hour|hours|day|days)\s+ago", cleaned.lower())
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit.startswith("minute"):
            return (now - timedelta(minutes=amount)).isoformat()
        if unit.startswith("hour"):
            return (now - timedelta(hours=amount)).isoformat()
        return (now - timedelta(days=amount)).isoformat()

    current_year = now.year
    for fmt in ("%d %b %Y", "%d %B %Y", "%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:
            parsed = parsed.replace(year=current_year)
        return parsed.replace(tzinfo=timezone.utc).isoformat()
    return None


def _source_metadata(node: ElementTree.Element | None) -> tuple[str, str]:
    """Extract publisher metadata from a Google News RSS source node."""

    if node is None:
        return "", ""
    publisher_name = normalize_whitespace(" ".join(fragment.strip() for fragment in node.itertext() if fragment.strip()))
    publisher_url = normalize_whitespace(node.attrib.get("url", ""))
    return publisher_name, publisher_url


def _source_label(label: str, query: str, publisher_name: str) -> str:
    """Build a more specific source label that carries the publisher when available."""

    if not publisher_name:
        return f"{label}: {query}"
    return f"{label}: {query} · {publisher_name}"


def _item_body(title: str, description: str | None, publisher_name: str) -> str:
    """Turn thin Google News RSS blurbs into readable, source-explicit bodies."""

    cleaned = normalize_whitespace(strip_tags(description or title))
    lowered = cleaned.lower()
    title_lower = title.lower()
    publisher_lower = publisher_name.lower().strip()
    thin_variants = {title_lower}
    if publisher_lower:
        thin_variants.add(f"{title_lower} {publisher_lower}")
    if lowered in thin_variants and publisher_name:
        return f"{title} Reported by {publisher_name} via Google News."
    return cleaned or title


def _search_result_metadata(title: str, aria_label: str) -> tuple[str, str | None, str | None]:
    """Extract publisher, date, and author metadata from a result-card aria-label."""

    normalized_title = normalize_whitespace(title)
    normalized_label = normalize_whitespace(aria_label)
    tail = normalized_label
    if normalized_title and normalized_label.startswith(f"{normalized_title} - "):
        tail = normalized_label[len(normalized_title) + 3 :]
    segments = [segment.strip() for segment in tail.split(" - ") if segment.strip()]
    if not segments:
        return "", None, None

    publisher_name = segments[0]
    date_text: str | None = None
    author_name: str | None = None
    for segment in segments[1:]:
        if segment.lower().startswith("by "):
            author_name = segment[3:].strip() or None
        elif date_text is None:
            date_text = segment
    return publisher_name, date_text, author_name


def _search_result_body(
    title: str,
    publisher_name: str,
    date_text: str | None,
    author_name: str | None,
) -> str:
    """Render search-card metadata into a readable summary body."""

    fragments = []
    if publisher_name:
        fragments.append(f"Reported by {publisher_name} via Google News")
    else:
        fragments.append("Reported via Google News")
    if date_text:
        fragments.append(f"on {date_text}")
    summary = " ".join(fragments).strip()
    if author_name:
        summary = f"{summary}. By {author_name}"
    return f"{summary}.".replace("..", ".")