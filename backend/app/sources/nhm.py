"""National Health Mission public page ingestion."""

from __future__ import annotations

from app.config import AppConfig, NHM_EXCLUDE_KEYWORDS, NHM_INCLUDE_KEYWORDS
from app.html_utils import parse_anchors, resolve_url
from app.models import ContentItem
from app.sources.base import SourceError, extract_pdf_text, fetch_text


class NhmSource:
    """Collect public monitoring and program references from NHM."""

    name = "nhm"
    label = "National Health Mission"
    url = "https://www.nhm.gov.in/"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch and filter NHM anchors with disease, program, and report relevance."""

        html = fetch_text(self.url, config)
        anchors = parse_anchors(html)
        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        for anchor in anchors:
            text = anchor.text.strip()
            if len(text) < 10:
                continue
            lowered = text.lower()
            if any(fragment in lowered for fragment in NHM_EXCLUDE_KEYWORDS):
                continue
            if not any(fragment in lowered for fragment in NHM_INCLUDE_KEYWORDS):
                continue
            absolute_url = resolve_url(self.url, anchor.href)
            if ".pdf" not in absolute_url.lower() and "index" in absolute_url.lower():
                continue
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            body = (
                "National Health Mission public reference: "
                f"{text}"
            )
            if absolute_url.lower().endswith(".pdf"):
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
                break
        return items
