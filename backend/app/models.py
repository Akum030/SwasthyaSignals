"""Domain models for normalized content and signal summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ContentItem:
    """A normalized piece of source content."""

    source: str
    source_label: str
    title: str
    body: str
    url: str
    published_at: str | None
    region: str = "Unknown"
    official: bool = False
    language: str = "unknown"
    sentiment: str = "neutral"
    adr_like: bool = False
    entities: dict[str, list[str]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def merged_text(self) -> str:
        """Return the full textual payload for analysis."""

        return "\n".join(part for part in (self.title, self.body) if part).strip()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the item for JSON output."""

        return asdict(self)


@dataclass(slots=True)
class SourceStatus:
    """Health summary for a source connector run."""

    name: str
    label: str
    ok: bool
    item_count: int
    message: str
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the status for JSON output."""

        return asdict(self)


@dataclass(slots=True)
class SignalCard:
    """Explainable signal summary derived from normalized evidence."""

    title: str
    summary: str
    confidence: int
    tags: list[str]
    evidence_count: int
    sources: list[str]
    official_references: list[str]
    example_urls: list[str]
    region: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the signal for JSON output."""

        return asdict(self)
