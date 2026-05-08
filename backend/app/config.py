"""Configuration and domain lexicons for SwasthyaSignals."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv


UPLOADED_DEMO_URL = "https://youtu.be/jnGYBJNrnSk"
LEGACY_DEMO_URLS = {
    "/app/",
    "https://swasthyasignals.aidhunik.com/app/",
    "https://swasthyasignals.lehana.in/app/",
}


def _resolve_demo_url() -> str:
    """Prefer the uploaded walkthrough when the environment still carries the old app redirect."""

    configured = getenv("SWASTHYA_DEMO_URL", "").strip()
    if not configured or configured in LEGACY_DEMO_URLS:
        return UPLOADED_DEMO_URL
    return configured


@dataclass(frozen=True)
class AppConfig:
    """Runtime settings for the ingestion prototype."""

    request_timeout_seconds: int = int(getenv("SWASTHYA_TIMEOUT", "20"))
    max_items_per_source: int = int(getenv("SWASTHYA_MAX_ITEMS", "10"))
    user_agent: str = getenv(
        "SWASTHYA_USER_AGENT",
        (
            "SwasthyaSignals/0.1 "
            "(hackathon research prototype; contact: local-dev)"
        ),
    )
    server_host: str = getenv("SERVER_HOST", "local-swasthya-signals")
    demo_url: str = _resolve_demo_url()
    version: str = "0.3.0"
    reddit_subreddits: tuple[str, ...] = (
        "diabetes",
        "hypertension",
        "asthma",
        "AskDocs",
    )
    reddit_search_queries: tuple[str, ...] = (
        "metformin palpitations",
        "semaglutide nausea india",
        "insulin brain fog",
        "hypertension medication side effect",
        "asthma air pollution delhi",
    )
    news_search_queries: tuple[str, ...] = (
        "India diabetes drug side effects",
        "India air pollution asthma",
        "India hypertension medicine safety",
        "India obesity lifestyle risk",
    )
    youtube_channels: tuple[tuple[str, str], ...] = (
        ("WHO", "@WHO"),
        ("Mayo Clinic", "@MayoClinic"),
        ("The Liver Doc", "@TheLiverDoc"),
    )
    telegram_channels: tuple[tuple[str, str], ...] = (
        ("MyGov India", "mygovindia"),
        ("MyGov Corona Newsdesk", "mygovcoronanewsdesk"),
        ("India Fights Corona", "IndiaFightsCorona"),
    )


ENTITY_LEXICONS: dict[str, tuple[str, ...]] = {
    "drugs": (
        "metformin",
        "insulin",
        "semaglutide",
        "ozempic",
        "mounjaro",
        "tirzepatide",
        "jardiance",
        "farxiga",
        "statin",
        "glipizide",
        "dexcom",
        "libre",
    ),
    "symptoms": (
        "palpitations",
        "nausea",
        "rash",
        "headache",
        "fatigue",
        "breathlessness",
        "shortness of breath",
        "neuropathy",
        "tingling",
        "dizziness",
        "vomiting",
        "cough",
        "fever",
        "wheezing",
        "anxiety",
        "brain fog",
        "chest pain",
        "chest tightness",
        "angina",
        "hair loss",
        "hair fall",
        "hair thinning",
        "alopecia",
        "nose bleeding",
        "nose bleeds",
        "nosebleed",
        "nosebleeds",
        "epistaxis",
        "bloody nose",
    ),
    "conditions": (
        "diabetes",
        "prediabetes",
        "obesity",
        "hypertension",
        "asthma",
        "copd",
        "mental health",
        "anaemia",
        "anemia",
        "sickle cell",
        "heart disease",
        "cardiovascular",
        "thyroid",
        "dengue",
        "covid",
        "tuberculosis",
    ),
    "lifestyle": (
        "sugar",
        "rice",
        "oil",
        "pollution",
        "smoking",
        "alcohol",
        "sedentary",
        "exercise",
        "sleep",
        "diet",
        "ultra processed",
        "air pollution",
        "weight loss",
    ),
}


PROJECT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "metformin": ("glycomet", "cetapin", "glucophage"),
    "semaglutide": ("ozempic", "wegovy", "rybelsus"),
    "tirzepatide": ("mounjaro", "zepbound"),
    "insulin": ("lantus", "humalog", "novorapid"),
    "blood sugar": ("glucose", "a1c", "hba1c", "glycemic"),
    "hypertension": ("high blood pressure", "bp"),
    "asthma": ("inhaler", "bronchial asthma"),
    "pollution": ("pm2.5", "aqi", "smog", "air quality"),
    "child": ("children", "pediatric", "paediatric", "adolescent", "school"),
    "diabetes": ("t1d", "t2d", "type 1 diabetes", "type 2 diabetes"),
    "chest pain": ("chest tightness", "angina"),
    "hair loss": ("hair fall", "hair thinning", "alopecia"),
    "nose bleeding": (
        "nose bleeds",
        "nosebleed",
        "nosebleeds",
        "epistaxis",
        "bloody nose",
        "nasal bleeding",
    ),
}


NEGATIVE_CUES: tuple[str, ...] = (
    "worse",
    "concern",
    "panic",
    "unsafe",
    "shortage",
    "complaint",
    "issue",
    "problem",
    "pain",
    "risk",
    "severe",
    "adverse",
    "side effect",
    "recall",
    "warning",
)


POSITIVE_CUES: tuple[str, ...] = (
    "improved",
    "better",
    "stable",
    "helped",
    "controlled",
    "normal",
    "recovery",
    "safe",
)


OFFICIAL_KEYWORDS: tuple[str, ...] = (
    "health",
    "disease",
    "drug",
    "medicine",
    "safety",
    "advisory",
    "guideline",
    "guidance",
    "alert",
    "notice",
    "quality",
    "complaint",
    "vaccin",
    "pollution",
    "diabetes",
    "hypertension",
    "obesity",
    "asthma",
    "tb",
    "tuberculosis",
    "mental health",
    "anaemia",
    "anemia",
    "sickle cell",
    "ncd",
)


HEALTH_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "doctor",
    "hospital",
    "clinic",
    "symptom",
    "symptoms",
    "diagnos",
    "disease",
    "condition",
    "medicine",
    "medication",
    "drug",
    "side effect",
    "adverse",
    "blood sugar",
    "blood pressure",
    "pollution",
    "vaccine",
    "therapy",
    "treatment",
    "patient",
    "health",
)


OFFICIAL_EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "vacancy",
    "recruitment",
    "tender",
    "bid no",
    "corrigendum",
    "software service provider",
    "rfp",
    "gem/",
    "assistant",
    "director",
    "deputy director",
    "hackathon",
)


CDSCO_INCLUDE_KEYWORDS: tuple[str, ...] = (
    "alert",
    "public notice",
    "guideline",
    "guidance",
    "drug",
    "drugs",
    "quality",
    "complaint",
    "vaccine",
    "vaccines",
    "cough syrup",
    "medical device",
    "biologic",
    "biologics",
    "recall",
    "safety",
    "adverse",
)


NHM_INCLUDE_KEYWORDS: tuple[str, ...] = (
    "np-ncd",
    "ncd",
    "diabetes",
    "hypertension",
    "mental health",
    "tuberculosis",
    "tb",
    "sickle",
    "anaemia",
    "anemia",
    "asthma",
    "copd",
    "campaign",
    "mis report",
    "guideline",
    "guidelines",
    "operational",
    "training module",
    "medical units",
    "mmu",
)


NHM_EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "innovation summit",
    "best practices shaping",
    "gallery",
    "success stories",
    "communitisation",
    "community action",
)


MOHFW_INCLUDE_KEYWORDS: tuple[str, ...] = (
    "view event",
    "world health",
    "press release",
    "pressreleasepage",
    "advisory",
    "public health",
    "vaccin",
    "disease",
    "ncd",
    "mental health",
    "tuberculosis",
)


INDIA_REGIONS: tuple[str, ...] = (
    "india",
    "delhi",
    "mumbai",
    "chennai",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "kolkata",
    "pune",
    "ncr",
    "maharashtra",
    "tamil nadu",
    "karnataka",
    "telangana",
    "gujarat",
    "uttar pradesh",
    "kerala",
)
