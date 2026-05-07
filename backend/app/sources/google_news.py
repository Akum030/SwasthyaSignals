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
                seen_urls.add(link)
                items.append(
                    ContentItem(
                        source=self.name,
                        source_label=f"{self.label}: {query}",
                        title=title,
                        body=strip_tags(node.findtext("description") or title),
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