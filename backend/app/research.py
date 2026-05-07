"""Research-backed source catalog and differentiators for the prototype."""

from __future__ import annotations

from urllib.parse import quote_plus

from app.config import AppConfig


CONFIG = AppConfig()


def _resource_link(label: str, url: str) -> dict[str, str]:
    return {"label": label, "url": url}


def _reddit_resource_links(config: AppConfig) -> list[dict[str, str]]:
    return [
        _resource_link(f"r/{subreddit}", f"https://www.reddit.com/r/{subreddit}/")
        for subreddit in config.reddit_subreddits
    ]


def _google_news_resource_links(config: AppConfig) -> list[dict[str, str]]:
    return [
        _resource_link(
            query,
            f"https://news.google.com/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en",
        )
        for query in config.news_search_queries
    ]


def _youtube_resource_links(config: AppConfig) -> list[dict[str, str]]:
    return [
        _resource_link(label, f"https://www.youtube.com/{handle}/videos")
        for label, handle in config.youtube_channels
    ]


def _telegram_resource_links(config: AppConfig) -> list[dict[str, str]]:
    return [
        _resource_link(label, f"https://t.me/s/{handle}")
        for label, handle in config.telegram_channels
    ]


SOURCE_CATALOG: list[dict[str, object]] = [
    {
        "name": "reddit",
        "label": "Reddit public JSON + keyword search",
        "method": "Unauthenticated subreddit listings plus targeted public search queries.",
        "best_for": "Patient complaints, caregiver narratives, and India-specific symptom-drug chatter.",
        "credentials": "None for MVP listing endpoints",
        "risk": "Moderation and misinformation noise; treat as early evidence, not ground truth.",
        "mvp": True,
        "resource_url": "https://www.reddit.com/",
        "resource_links": _reddit_resource_links(CONFIG),
    },
    {
        "name": "google_news",
        "label": "Google News RSS validation feed",
        "method": "Public RSS search over India-focused health risk queries.",
        "best_for": "Near-real-time corroboration from open news coverage without API keys.",
        "credentials": "None",
        "risk": "Aggregator coverage varies by topic; use as corroboration, not sole evidence.",
        "mvp": True,
        "resource_url": "https://news.google.com/",
        "resource_links": _google_news_resource_links(CONFIG),
    },
    {
        "name": "cdsco",
        "label": "CDSCO alerts and notices",
        "method": "Homepage PDF notice scrape with safety and quality filters.",
        "best_for": "Drug quality complaints, recalls, regulatory updates, safety context.",
        "credentials": "None",
        "risk": "Website layout changes can affect scraping selectors.",
        "mvp": True,
        "resource_url": "https://cdsco.gov.in/opencms/opencms/en/Home/",
        "resource_links": [
            _resource_link("CDSCO consumer updates", "https://cdsco.gov.in/opencms/opencms/en/consumer/"),
        ],
    },
    {
        "name": "nhm",
        "label": "National Health Mission",
        "method": "What’s New and program-document scrape with NCD-focused filters.",
        "best_for": "Program guidelines, NP-NCD training updates, MIS reports, and campaign references.",
        "credentials": "None",
        "risk": "Broader mission content needs topic filters to stay signal-rich.",
        "mvp": True,
        "resource_url": "https://nhm.gov.in/",
        "resource_links": [
            _resource_link("NHM What's New", "https://nhm.gov.in/index1.php?lang=1&level=1&sublinkid=82&lid=74"),
        ],
    },
    {
        "name": "data_gov",
        "label": "data.gov.in health datasets",
        "method": "Public RSS dataset feed filtered for health, disease, and air-quality indicators.",
        "best_for": "Authentic Indian baseline datasets for air quality, disease burden, and public-health context.",
        "credentials": "None",
        "risk": "This is baseline context, not early-warning social chatter.",
        "mvp": True,
        "resource_url": "https://www.data.gov.in/",
        "resource_links": [
            _resource_link("Health datasets", "https://www.data.gov.in/catalogs?title=health"),
            _resource_link("Air quality datasets", "https://www.data.gov.in/catalogs?title=air%20quality"),
        ],
    },
    {
        "name": "youtube",
        "label": "YouTube public channel RSS",
        "method": "Resolve curated public channel handles to open RSS feeds and ingest recent video titles plus descriptions.",
        "best_for": "Expert explainers, regulator/community education, and fast video-based corroboration without API keys.",
        "credentials": "None for public channels",
        "risk": "Coverage depends on curated channels and public descriptions can be short or promotional.",
        "mvp": True,
        "resource_url": "https://www.youtube.com/",
        "resource_links": _youtube_resource_links(CONFIG),
    },
    {
        "name": "telegram",
        "label": "Telegram public channel mirrors",
        "method": "Scrape curated public /s/ channel mirrors and extract recent message text plus permalinks.",
        "best_for": "Government broadcast notices, campaign messaging, and rapid public updates that never reach RSS.",
        "credentials": "None for public broadcast channels",
        "risk": "Only some channels expose public mirror pages, so the allowlist must stay curated.",
        "mvp": True,
        "resource_url": "https://t.me/",
        "resource_links": _telegram_resource_links(CONFIG),
    },
    {
        "name": "mohfw",
        "label": "MoHFW public site",
        "method": "Homepage event discovery for manual or future enhanced capture.",
        "best_for": "Pointer layer into ministry messaging when a richer renderer is available.",
        "credentials": "None",
        "risk": "Current site rendering is not reliable for direct no-JS scraping, so it is not in the live MVP path.",
        "mvp": False,
        "resource_url": "https://mohfw.gov.in/",
        "resource_links": [],
    },
    {
        "name": "nfhs_gbd",
        "label": "NFHS / GBD reference baselines",
        "method": "Public dataset import and periodic refresh.",
        "best_for": "State-level burden baselines and India-vs-world framing.",
        "credentials": "None",
        "risk": "Lagged data, better for context than early detection.",
        "mvp": False,
        "resource_url": "https://www.dhsprogram.com/Methodology/Survey-Search.cfm?Country=India",
        "resource_links": [
            _resource_link("India NFHS surveys", "https://www.dhsprogram.com/Methodology/Survey-Search.cfm?Country=India"),
            _resource_link("IHME GBD", "https://www.healthdata.org/research-analysis/gbd"),
        ],
    },
]


DIFFERENTIATORS: list[str] = [
    (
        "Fuse patient chatter with Indian regulatory notices so a complaint spike "
        "can be judged against real official movement instead of standing alone."
    ),
    (
        "Exploit public no-key acquisition paths that most teams ignore, especially "
        "Reddit keyword search, Google News RSS, and data.gov.in dataset feeds, so "
        "the live demo does not depend on sponsor-only API access."
    ),
    (
        "Treat India-specific lifestyle context as first-class evidence, especially "
        "diet, pollution, and chronic-disease risk combinations that generic global "
        "tools usually ignore."
    ),
    (
        "Keep explainability close to the evidence by exposing the phrases, sources, "
        "and official references that produced each signal card."
    ),
]


MVP_STRATEGY: dict[str, object] = {
    "priority": ["reddit", "google_news", "youtube", "telegram", "cdsco", "nhm", "data_gov"],
    "stretch": ["nfhs_gbd"],
    "guiding_rule": (
        "Use only sources that can be refreshed today without sponsor-only access, "
        "triangulate social, news, Indian official notices, and open government "
        "datasets, then layer optional connectors once the live no-key core is stable."
    ),
}
