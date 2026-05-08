"""Google News RSS ingestion for public health validation."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree

from app.config import AppConfig
from app.html_utils import normalize_whitespace, strip_tags
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


class GoogleNewsSource:
    """Collect India-focused health stories from Google News RSS."""

    name = "google_news"
    label = "Google News RSS"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch a small, query-focused set of public news entries."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        query_count = max(1, len(config.news_search_queries))
        limit_per_query = max(2, config.max_items_per_source // query_count)

        for query in config.news_search_queries:
            url = (
                "https://news.google.com/rss/search"
                f"?q={quote_plus(f'{query} when:30d')}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            xml_text = fetch_text(url, config)
            try:
                root = ElementTree.fromstring(xml_text)
            except ElementTree.ParseError as error:
                raise SourceError(f"{url} -> invalid RSS payload") from error

            collected = 0
            for node in root.findall(".//item"):
                title = normalize_whitespace((node.findtext("title") or "").replace(" - Google News", ""))
                link = normalize_whitespace(node.findtext("link") or "")
                if not title or not link or link in seen_urls:
                    continue
                publisher_name, _publisher_url = _source_metadata(node.find("source"))
                seen_urls.add(link)
                items.append(
                    ContentItem(
                        source=self.name,
                        source_label=_source_label(self.label, query, publisher_name),
                        title=title,
                        body=_item_body(title, node.findtext("description"), publisher_name),
                        url=link,
                        published_at=_parse_pub_date(node.findtext("pubDate")),
                    )
                )
                collected += 1
                if collected >= limit_per_query:
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