"""Orchestrate real-source collection into a dashboard snapshot."""

from __future__ import annotations

from app.config import AppConfig
from app.models import ContentItem, SourceStatus
from app.pipeline import build_signals, enrich_item, filter_relevant_items, summarize_topics, utc_now_iso
from app.sources.base import SourceError
from app.sources.cdsco import CdscoSource
from app.sources.data_gov import DataGovSource
from app.sources.google_news import GoogleNewsSource
from app.sources.nhm import NhmSource
from app.sources.reddit import RedditSource
from app.sources.telegram import TelegramSource
from app.sources.youtube import YouTubeSource


MAX_SNAPSHOT_ITEMS = 80


def collect_snapshot(config: AppConfig | None = None) -> dict[str, object]:
    """Collect a real-time snapshot across live public sources."""

    active_config = config or AppConfig()
    connectors = [
        RedditSource(),
        GoogleNewsSource(),
        YouTubeSource(),
        TelegramSource(),
        NhmSource(),
        DataGovSource(),
        CdscoSource(),
    ]
    items: list[ContentItem] = []
    statuses: list[SourceStatus] = []

    for connector in connectors:
        fetched_at = utc_now_iso()
        try:
            raw_items = connector.fetch(active_config)
            enriched = [enrich_item(item) for item in raw_items]
            items.extend(enriched)
            statuses.append(
                SourceStatus(
                    name=connector.name,
                    label=connector.label,
                    ok=True,
                    item_count=len(enriched),
                    message="ok",
                    fetched_at=fetched_at,
                )
            )
        except SourceError as error:
            statuses.append(
                SourceStatus(
                    name=connector.name,
                    label=connector.label,
                    ok=False,
                    item_count=0,
                    message=str(error),
                    fetched_at=fetched_at,
                )
            )

    relevant_items = filter_relevant_items(items)
    relevant_items.sort(
        key=lambda item: item.published_at or "",
        reverse=True,
    )
    signals = build_signals(relevant_items)

    return {
        "generated_at": utc_now_iso(),
        "version": active_config.version,
        "server_host": active_config.server_host,
        "item_count": len(relevant_items),
        "signal_count": len(signals),
        "source_status": [status.to_dict() for status in statuses],
        "topics": summarize_topics(relevant_items),
        "signals": [signal.to_dict() for signal in signals],
        "items": [item.to_dict() for item in relevant_items[:MAX_SNAPSHOT_ITEMS]],
    }
