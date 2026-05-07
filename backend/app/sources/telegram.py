"""Telegram public channel mirror ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

from app.config import AppConfig
from app.html_utils import normalize_whitespace
from app.models import ContentItem
from app.sources.base import SourceError, fetch_text


TITLE_SPLIT_PATTERN = re.compile(r"[.!?\n]+")


@dataclass(slots=True)
class _TelegramMessage:
    url: str
    published_at: str | None
    body: str


class _TelegramMessageParser(HTMLParser):
    """Capture Telegram /s/ message permalinks, timestamps, and text blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[_TelegramMessage] = []
        self._current_url: str | None = None
        self._current_published_at: str | None = None
        self._body_parts: list[str] = []
        self._in_body = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        css_class = attributes.get("class") or ""
        if tag == "a" and "tgme_widget_message_date" in css_class:
            self._flush_current()
            self._current_url = normalize_whitespace(attributes.get("href") or "")
            self._current_published_at = None
            self._body_parts = []
            return
        if tag == "time" and self._current_url:
            self._current_published_at = normalize_whitespace(attributes.get("datetime") or "") or None
            return
        if tag == "div" and "tgme_widget_message_text" in css_class and self._current_url:
            self._in_body = True
            self._body_parts = []
            return
        if tag == "br" and self._in_body:
            self._body_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_body:
            self._body_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_body:
            self._in_body = False
            self._flush_current()

    def close(self) -> None:
        super().close()
        self._flush_current()

    def _flush_current(self) -> None:
        body = normalize_whitespace(" ".join(self._body_parts))
        if self._current_url and body:
            self.messages.append(
                _TelegramMessage(
                    url=self._current_url,
                    published_at=self._current_published_at,
                    body=body,
                )
            )
        self._body_parts = []


class TelegramSource:
    """Collect recent messages from curated public Telegram channel mirrors."""

    name = "telegram"
    label = "Telegram public channel mirrors"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch recent messages from configured public /s/ channels."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        errors: list[str] = []
        channel_count = max(1, len(config.telegram_channels))
        limit_per_channel = max(2, config.max_items_per_source // channel_count)

        for label, channel in config.telegram_channels:
            try:
                html = fetch_text(f"https://t.me/s/{channel}", config)
                items.extend(
                    _parse_channel_messages(html, label, seen_urls, limit_per_channel)
                )
            except SourceError as error:
                errors.append(str(error))

        if items or not errors:
            return items
        raise SourceError("; ".join(errors[:2]))


def _parse_channel_messages(
    html: str,
    channel_label: str,
    seen_urls: set[str],
    limit: int,
) -> list[ContentItem]:
    """Parse a Telegram /s/ channel page into normalized items."""

    parser = _TelegramMessageParser()
    parser.feed(html)
    parser.close()

    items: list[ContentItem] = []
    for message in parser.messages:
        if message.url in seen_urls:
            continue
        seen_urls.add(message.url)
        items.append(
            ContentItem(
                source="telegram",
                source_label=f"Telegram: {channel_label}",
                title=_body_to_title(message.body),
                body=message.body,
                url=message.url,
                published_at=message.published_at,
            )
        )
        if len(items) >= limit:
            break
    return items


def _body_to_title(body: str) -> str:
    """Create a short headline-like title from a Telegram message body."""

    candidate = TITLE_SPLIT_PATTERN.split(body.strip(), maxsplit=1)[0].strip() or body.strip()
    words = candidate.split()
    if len(words) <= 16:
        return candidate
    return f"{' '.join(words[:16])}..."