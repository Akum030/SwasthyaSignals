"""Base helpers for source connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import AppConfig


class SourceError(RuntimeError):
    """Raised when a source connector fails."""


def fetch_bytes(url: str, config: AppConfig) -> bytes:
    """Fetch raw bytes from a remote URL."""

    request = Request(url, headers={"User-Agent": config.user_agent})
    try:
        with urlopen(request, timeout=config.request_timeout_seconds) as response:
            return response.read()
    except (HTTPError, URLError) as error:
        raise SourceError(f"{url} -> {error}") from error


def fetch_text(url: str, config: AppConfig) -> str:
    """Fetch text content from a remote URL."""

    request = Request(url, headers={"User-Agent": config.user_agent})
    try:
        with urlopen(request, timeout=config.request_timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError) as error:
        raise SourceError(f"{url} -> {error}") from error


def fetch_json(url: str, config: AppConfig) -> dict:
    """Fetch a JSON payload from a remote URL."""

    return json.loads(fetch_text(url, config))


def extract_pdf_text(
    url: str,
    config: AppConfig,
    *,
    max_pages: int = 4,
    max_chars: int = 7000,
) -> str:
    """Extract a bounded amount of text from a PDF for keyword matching."""

    return _extract_pdf_text_cached(
        url,
        config.user_agent,
        config.request_timeout_seconds,
        max_pages,
        max_chars,
    )


@lru_cache(maxsize=64)
def _extract_pdf_text_cached(
    url: str,
    user_agent: str,
    timeout_seconds: int,
    max_pages: int,
    max_chars: int,
) -> str:
    """Cache PDF text extraction so repeated refreshes do not reparse identical files."""

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise SourceError("pypdf is required for official PDF extraction") from error

    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except (HTTPError, URLError) as error:
        raise SourceError(f"{url} -> {error}") from error

    try:
        reader = PdfReader(BytesIO(payload))
    except Exception as error:
        raise SourceError(f"{url} -> unable to parse PDF") from error

    fragments: list[str] = []
    consumed = 0
    for page_number, page in enumerate(reader.pages):
        if page_number >= max_pages or consumed >= max_chars:
            break
        raw_text = page.extract_text() or ""
        clean_text = " ".join(raw_text.split())
        if not clean_text:
            continue
        remaining = max_chars - consumed
        excerpt = clean_text[:remaining]
        fragments.append(excerpt)
        consumed += len(excerpt)

    return " ".join(fragments)


def created_to_iso(timestamp: float | int | None) -> str | None:
    """Convert an epoch timestamp into ISO-8601."""

    if timestamp is None:
        return None
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
