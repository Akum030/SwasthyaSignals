"""CDSCO public alerts and notices ingestion."""

from __future__ import annotations

from app.config import (
    AppConfig,
    CDSCO_INCLUDE_KEYWORDS,
    OFFICIAL_EXCLUDE_KEYWORDS,
)
from app.html_utils import parse_anchors, resolve_url
from app.models import ContentItem
from app.sources.base import SourceError, extract_pdf_text, fetch_text


class CdscoSource:
    """Collect safety and regulatory references from CDSCO."""

    name = "cdsco"
    label = "CDSCO"
    url = "https://cdsco.gov.in/opencms/opencms/en/"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch and filter high-signal PDF notices from the CDSCO homepage."""

        html = fetch_text(self.url, config)
        anchors = parse_anchors(html)
        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        for anchor in anchors:
            text = anchor.text.strip()
            if len(text) < 18:
                continue
            lowered = text.lower()
            href = anchor.href.lower()
            if any(keyword in lowered for keyword in OFFICIAL_EXCLUDE_KEYWORDS):
                continue
            if href.endswith("/") or ".pdf" not in href:
                continue
            if not any(keyword in lowered for keyword in CDSCO_INCLUDE_KEYWORDS):
                continue
            absolute_url = resolve_url(self.url, anchor.href)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            body = f"CDSCO safety or regulatory update: {text}"
            try:
                pdf_excerpt = extract_pdf_text(absolute_url, config)
            except SourceError:
                pdf_excerpt = ""
            if pdf_excerpt:
                body = f"{body} {pdf_excerpt}"
            items.append(
                ContentItem(
                    source=self.name,
                    source_label=self.label,
                    title=text,
                    body=body,
                    url=absolute_url,
                    published_at=None,
                    official=True,
                )
            )
            if len(items) >= config.max_items_per_source:
                return items
        return items
