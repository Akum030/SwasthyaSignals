"""Endpoint regression tests for the FastAPI application shell."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import app.main as main_module
from app.main import app
from app.schemas import ProjectRequest


class MainRouteTests(unittest.TestCase):
    """Verify entry routes stay stable for the live prototype."""

    @staticmethod
    def _get_route(path: str):
        for route in app.routes:
            if getattr(route, "path", None) == path:
                return route
        raise AssertionError(f"Route not found: {path}")

    def test_root_redirects_to_app(self) -> None:
        """The bare domain should open the command-center UI."""

        response = self._get_route("/").endpoint()

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/app/")

    def test_demo_redirect_defaults_to_app(self) -> None:
        """The stable demo URL should exist even before the final hosted video is attached."""

        response = self._get_route("/demo").endpoint()

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/app/")

    def test_analyze_project_uses_stale_snapshot_while_refreshing_in_background(self) -> None:
        """Stale caches should still serve immediately instead of blocking the request path."""

        route = self._get_route("/api/v1/projects/analyze")
        project = ProjectRequest(keywords=["nose bleeding"], latency_profile="Realtime")
        stale_snapshot = {"generated_at": "2026-05-08T00:00:00+00:00", "items": [], "source_status": []}

        with patch.object(main_module, "SNAPSHOT_CACHE", stale_snapshot), patch.object(
            main_module,
            "_should_refresh_snapshot",
            return_value=True,
        ), patch.object(main_module, "_schedule_snapshot_refresh") as schedule_refresh, patch.object(
            main_module,
            "_refresh_snapshot",
        ) as refresh_snapshot, patch.object(
            main_module,
            "build_project_view",
            return_value={"ok": True},
        ) as build_view:
            response = route.endpoint(project)

        self.assertEqual(response, {"ok": True})
        schedule_refresh.assert_called_once_with()
        refresh_snapshot.assert_not_called()
        build_view.assert_called_once_with(stale_snapshot, project.model_dump())

    def test_analyze_project_refreshes_synchronously_when_cache_missing(self) -> None:
        """Cold starts still need one synchronous refresh because there is nothing to serve yet."""

        route = self._get_route("/api/v1/projects/analyze")
        project = ProjectRequest(keywords=["metformin"], latency_profile="Realtime")
        fresh_snapshot = {"generated_at": "2026-05-08T00:00:00+00:00", "items": [], "source_status": []}

        with patch.object(main_module, "SNAPSHOT_CACHE", None), patch.object(
            main_module,
            "_refresh_snapshot",
            return_value=fresh_snapshot,
        ) as refresh_snapshot, patch.object(
            main_module,
            "_schedule_snapshot_refresh",
        ) as schedule_refresh, patch.object(
            main_module,
            "build_project_view",
            return_value={"ok": True},
        ) as build_view:
            response = route.endpoint(project)

        self.assertEqual(response, {"ok": True})
        refresh_snapshot.assert_called_once_with()
        schedule_refresh.assert_not_called()
        build_view.assert_called_once_with(fresh_snapshot, project.model_dump())


if __name__ == "__main__":
    unittest.main()