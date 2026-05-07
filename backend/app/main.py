"""FastAPI application for the SwasthyaSignals prototype."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import AppConfig
from app.projects import DEFAULT_PROJECTS, build_project_view
from app.research import DIFFERENTIATORS, MVP_STRATEGY, SOURCE_CATALOG
from app.schemas import ProjectRequest
from app.snapshot import collect_snapshot
from app.storage import load_snapshot, save_snapshot


CONFIG = AppConfig()
STARTED_AT = datetime.now(tz=timezone.utc).isoformat()
SNAPSHOT_LOCK = Lock()
REFRESH_STATE_LOCK = Lock()
SNAPSHOT_CACHE: dict[str, object] | None = load_snapshot()
SNAPSHOT_REFRESH_IN_PROGRESS = False


def create_app() -> FastAPI:
    """Build the API application and mount the frontend when present."""

    app = FastAPI(title="SwasthyaSignals", version=CONFIG.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="app")

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def portal_root() -> RedirectResponse:
        """Make the domain root open the command-center UI directly."""

        return RedirectResponse(url="/app/", status_code=307)

    @app.api_route("/demo", methods=["GET", "HEAD"], include_in_schema=False)
    def demo_redirect() -> RedirectResponse:
        """Expose a stable demo URL that can later be repointed to a hosted video."""

        return RedirectResponse(url=CONFIG.demo_url, status_code=307)

    @app.api_route("/health", methods=["GET", "HEAD"])
    def health() -> dict[str, str]:
        """Return the standardized health payload."""

        return {
            "status": "ok",
            "started": STARTED_AT,
            "host": CONFIG.server_host,
            "version": CONFIG.version,
        }

    @app.get("/api/v1/snapshot")
    def get_snapshot(refresh: bool = False) -> dict[str, object]:
        """Return the current live snapshot, refreshing when requested."""

        return _refresh_snapshot() if refresh or SNAPSHOT_CACHE is None else SNAPSHOT_CACHE

    @app.get("/api/v1/projects/defaults")
    def get_default_projects() -> dict[str, object]:
        """Expose the built-in demo project presets."""

        return {"projects": DEFAULT_PROJECTS}

    @app.post("/api/v1/projects/analyze")
    def analyze_project(project: ProjectRequest, refresh: bool = False) -> dict[str, object]:
        """Build a project-scoped dashboard from the latest live snapshot."""

        snapshot = SNAPSHOT_CACHE
        if refresh or snapshot is None:
            snapshot = _refresh_snapshot()
        elif _should_refresh_snapshot(snapshot, project.latency_profile):
            _schedule_snapshot_refresh()
        return build_project_view(snapshot, project.model_dump())

    @app.get("/api/v1/research")
    def research() -> dict[str, object]:
        """Expose source strategy and differentiators to the frontend."""

        return {
            "source_catalog": SOURCE_CATALOG,
            "differentiators": DIFFERENTIATORS,
            "mvp_strategy": MVP_STRATEGY,
        }

    return app


def _refresh_snapshot() -> dict[str, object]:
    """Refresh the cached snapshot in a thread-safe way."""

    global SNAPSHOT_CACHE
    with SNAPSHOT_LOCK:
        SNAPSHOT_CACHE = collect_snapshot(CONFIG)
        save_snapshot(SNAPSHOT_CACHE)
        return SNAPSHOT_CACHE


def _schedule_snapshot_refresh() -> None:
    """Refresh stale snapshots in the background so searches do not block on slow sources."""

    global SNAPSHOT_REFRESH_IN_PROGRESS

    with REFRESH_STATE_LOCK:
        if SNAPSHOT_REFRESH_IN_PROGRESS:
            return
        SNAPSHOT_REFRESH_IN_PROGRESS = True

    Thread(target=_refresh_snapshot_in_background, daemon=True).start()


def _refresh_snapshot_in_background() -> None:
    """Execute a background snapshot refresh and release the in-progress guard."""

    global SNAPSHOT_REFRESH_IN_PROGRESS

    try:
        _refresh_snapshot()
    finally:
        with REFRESH_STATE_LOCK:
            SNAPSHOT_REFRESH_IN_PROGRESS = False


def _should_refresh_snapshot(snapshot: dict[str, object], latency_profile: str) -> bool:
    """Refresh stale snapshots based on the latency contract promised to the user."""

    generated_at = snapshot.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        return True

    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return True

    ttl_seconds = {
        "Realtime": 300,
        "Daily": 6 * 60 * 60,
        "Weekly": 24 * 60 * 60,
    }.get(latency_profile, 300)

    age_seconds = (datetime.now(tz=timezone.utc) - generated).total_seconds()
    return age_seconds >= ttl_seconds


app = create_app()
