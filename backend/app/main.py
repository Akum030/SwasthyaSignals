"""FastAPI application for the SwasthyaSignals prototype."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
SNAPSHOT_CACHE: dict[str, object] | None = load_snapshot()


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

    @app.get("/health")
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

        snapshot = _refresh_snapshot() if refresh or SNAPSHOT_CACHE is None else SNAPSHOT_CACHE
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


app = create_app()
