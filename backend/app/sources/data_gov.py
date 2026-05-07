"""data.gov.in RSS ingestion for baseline public-health datasets."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from app.config import AppConfig
from app.html_utils import strip_tags
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


INCLUDE_KEYWORDS = (
    "air quality",
    "pollution",
    "health",
    "disease",
    "hospital",
    "diabetes",
    "tuberculosis",
    "malaria",
    "immun",
    "vaccine",
    "pm2.5",
)


class DataGovSource:
    """Collect public baseline datasets relevant to Indian health monitoring."""

    name = "data_gov"
    label = "data.gov.in"
    url = "https://data.gov.in/backend/dms/v1/rss.xml"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch health-adjacent dataset entries from the public RSS feed."""

        xml_text = fetch_text(self.url, config)
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as error:
            raise SourceError(f"{self.url} -> invalid RSS payload") from error

        items: list[ContentItem] = []
        for node in root.findall(".//item"):
            title = _node_text(node.find("title"))
            description = _node_text(node.find("description"))
            merged = f"{title} {description}".lower()
            if not title or not any(keyword in merged for keyword in INCLUDE_KEYWORDS):
                continue
            link = (node.findtext("link") or "").strip()
            items.append(
                ContentItem(
                    source=self.name,
                    source_label=self.label,
                    title=title,
                    body=description or title,
                    url=link,
                    published_at=_parse_pub_date(node.findtext("pubDate")),
                    official=True,
                )
            )
            if len(items) >= config.max_items_per_source:
                break
        return items


def _parse_pub_date(raw_value: str | None) -> str | None:
    """Convert the RSS publication date into ISO-8601 when possible."""

    if not raw_value:
        return None
    try:
        return parsedate_to_datetime(raw_value).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


def _node_text(node: ElementTree.Element | None) -> str:
    """Extract visible text from an RSS node that may contain nested HTML."""

    if node is None:
        return ""
    raw_text = " ".join(fragment.strip() for fragment in node.itertext() if fragment.strip())
    return strip_tags(raw_text)