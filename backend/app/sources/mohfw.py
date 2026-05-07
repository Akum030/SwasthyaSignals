"""MoHFW public website ingestion."""

from __future__ import annotations

from app.config import AppConfig, MOHFW_INCLUDE_KEYWORDS
from app.html_utils import parse_anchors, resolve_url
from app.models import ContentItem
from app.sources.base import fetch_text


class MohfwSource:
    """Collect public health references from MoHFW."""

    name = "mohfw"
    label = "MoHFW"
    url = "https://www.mohfw.gov.in/"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch event and press-release links surfaced by the MoHFW homepage."""

        html = fetch_text(self.url, config)
        anchors = parse_anchors(html)
        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        for anchor in anchors:
            text = anchor.text.strip()
            if len(text) < 8:
                continue
            lowered = text.lower()
            href = anchor.href.lower()
            if not any(keyword in lowered or keyword in href for keyword in MOHFW_INCLUDE_KEYWORDS):
                continue
            absolute_url = resolve_url(self.url, anchor.href)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            items.append(
                ContentItem(
                    source=self.name,
                    source_label=self.label,
                    title=text,
                    body=f"MoHFW event or press reference: {text}",
                    url=absolute_url,
                    published_at=None,
                    official=True,
                )
            )
            if len(items) >= config.max_items_per_source:
                break
        return items
