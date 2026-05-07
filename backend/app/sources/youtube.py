"""YouTube public channel RSS ingestion."""

from __future__ import annotations

import re
from xml.etree import ElementTree

from app.config import AppConfig
from app.html_utils import normalize_whitespace
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
CHANNEL_ID_PATTERN = re.compile(r'externalId":"([^"]+)"')
FEED_URL_PATTERN = re.compile(r'https://www.youtube.com/feeds/videos.xml\?channel_id=([^"&]+)')


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
                items.extend(
                    _parse_feed_items(xml_text, label, seen_urls, limit_per_channel)
                )
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