"""Small HTML parsing helpers implemented with the standard library."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass(frozen=True)
class Anchor:
    """Minimal anchor representation."""

    href: str
    text: str


class AnchorCollector(HTMLParser):
    """Collect anchors and visible text from a page."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[Anchor] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track anchor start tags."""

        if tag != "a":
            return
        attributes = dict(attrs)
        self._current_href = attributes.get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        """Buffer text inside the current anchor."""

        if self._current_href is None:
            return
        self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finalize the current anchor."""

        if tag != "a" or self._current_href is None:
            return
        text = normalize_whitespace(" ".join(self._text_parts))
        href = normalize_whitespace(self._current_href)
        if href and text:
            self.anchors.append(Anchor(href=href, text=text))
        self._current_href = None
        self._text_parts = []


class TextCollector(HTMLParser):
    """Strip tags and keep visible text only."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Collect text fragments outside of markup."""

        self._parts.append(data)

    def text(self) -> str:
        """Return normalized visible text."""

        return normalize_whitespace(" ".join(self._parts))


class MetaContentCollector(HTMLParser):
    """Collect HTML meta tag content keyed by name or property."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Capture meta content attributes."""

        if tag != "meta":
            return
        attributes = dict(attrs)
        key = normalize_whitespace(
            attributes.get("property")
            or attributes.get("name")
            or ""
        ).lower()
        content = normalize_whitespace(attributes.get("content") or "")
        if key and content and key not in self.meta:
            self.meta[key] = content


def normalize_whitespace(value: str) -> str:
    """Collapse repeated whitespace and HTML entities."""

    return " ".join(unescape(value).split())


def parse_anchors(html: str) -> list[Anchor]:
    """Extract anchors from a raw HTML string."""

    parser = AnchorCollector()
    parser.feed(html)
    return parser.anchors


def strip_tags(value: str) -> str:
    """Convert a small HTML fragment into visible text."""

    parser = TextCollector()
    parser.feed(value)
    return parser.text()


def extract_meta_content(html: str, *keys: str) -> str:
    """Return the first matching meta content value from an HTML document."""

    parser = MetaContentCollector()
    parser.feed(html)
    for key in keys:
        value = parser.meta.get(key.lower())
        if value:
            return value
    return ""


def resolve_url(base_url: str, href: str) -> str:
    """Resolve relative links against a source base URL."""

    return urljoin(base_url, href)
