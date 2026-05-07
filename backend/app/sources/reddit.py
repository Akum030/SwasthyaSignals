"""Reddit public JSON ingestion."""

from __future__ import annotations

from urllib.parse import quote_plus

from app.config import AppConfig
from app.models import ContentItem
from app.sources.base import created_to_iso, fetch_json


class RedditSource:
    """Collect posts from public subreddit listings."""

    name = "reddit"
    label = "Reddit Public Listings"

    def fetch(self, config: AppConfig) -> list[ContentItem]:
        """Fetch recent posts from configured subreddits."""

        items: list[ContentItem] = []
        seen_urls: set[str] = set()
        bucket_count = max(1, len(config.reddit_subreddits) + len(config.reddit_search_queries))
        bucket_limit = max(2, config.max_items_per_source // bucket_count)
        for subreddit in config.reddit_subreddits:
            url = (
                f"https://www.reddit.com/r/{subreddit}/new.json"
                f"?limit={bucket_limit}&raw_json=1"
            )
            payload = fetch_json(url, config)
            items.extend(self._payload_to_items(payload, f"r/{subreddit}", seen_urls))

        for query in config.reddit_search_queries:
            url = (
                "https://www.reddit.com/search.json"
                f"?q={quote_plus(query)}&sort=new&t=month"
                f"&limit={bucket_limit}&raw_json=1"
            )
            payload = fetch_json(url, config)
            items.extend(self._payload_to_items(payload, f"search:{query}", seen_urls))
        return items

    def _payload_to_items(
        self,
        payload: dict,
        source_label: str,
        seen_urls: set[str],
    ) -> list[ContentItem]:
        """Convert a Reddit listing or search response into normalized items."""

        items: list[ContentItem] = []
        for child in payload.get("data", {}).get("children", []):
            data = child.get("data", {})
            permalink = data.get("permalink") or ""
            if not permalink or data.get("over_18"):
                continue
            url = f"https://www.reddit.com{permalink}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            items.append(
                ContentItem(
                    source=self.name,
                    source_label=source_label,
                    title=data.get("title", "Untitled post"),
                    body=data.get("selftext") or "",
                    url=url,
                    published_at=created_to_iso(data.get("created_utc")),
                )
            )
        return items
