"""Regression tests for project-scoped dashboard shaping."""

from __future__ import annotations

import unittest

from app.projects import DEFAULT_PROJECTS, _build_focus_queries, _expand_project_keywords, build_project_view


class ProjectViewTests(unittest.TestCase):
    """Verify project filtering keeps relevant evidence and rejects obvious noise."""

    def test_default_projects_offer_a_broad_library(self) -> None:
        """The portal should ship with a substantial preset library, not a tiny demo list."""

        self.assertGreaterEqual(len(DEFAULT_PROJECTS), 10)
        self.assertIn("Diabetes drugs - India vs World", [project["name"] for project in DEFAULT_PROJECTS])

    def test_build_focus_queries_stays_compact_for_narrow_brief(self) -> None:
        """Small custom briefs should not fan out into generic single-keyword searches."""

        queries = _build_focus_queries(["metformin", "palpitations"])

        self.assertIn("india metformin palpitations", queries)
        self.assertIn("metformin side effect", queries)
        self.assertNotIn("india metformin", queries)
        self.assertNotIn("india palpitations", queries)

    def test_build_focus_queries_drop_redundant_single_word_fragments(self) -> None:
        """Split words from the same phrase should not produce awkward duplicate live probes."""

        queries = _build_focus_queries(["hair loss", "hair", "loss"])

        self.assertIn("india hair loss", queries)
        self.assertNotIn("india hair loss hair", queries)
        self.assertNotIn("india hair loss loss", queries)

    def test_build_focus_queries_expand_symptom_aliases_for_narrow_phrase(self) -> None:
        """Symptom-only briefs should probe common clinical aliases, not just one literal phrase."""

        queries = _build_focus_queries(["nose bleeding", "nose", "bleeding"])

        self.assertIn("india nose bleeding", queries)
        self.assertIn("india nosebleed", queries)
        self.assertIn("india epistaxis", queries)

    def test_expand_project_keywords_adds_brand_aliases(self) -> None:
        """Canonical terms should expand to the same family as common brand-name aliases."""

        expanded = _expand_project_keywords(["metformin", "semaglutide"])

        self.assertIn("glycomet", expanded)
        self.assertIn("cetapin", expanded)
        self.assertIn("ozempic", expanded)
        self.assertIn("wegovy", expanded)

    def test_build_project_view_rejects_offtopic_reddit_search_result(self) -> None:
        """Search hits from non-health subreddits should not leak into a health brief."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Diabetes drugs - India vs World",
            "description": "Focus on diabetes medication and safety chatter.",
            "keywords": ["diabetes", "insulin", "metformin"],
            "sources": ["reddit"],
            "latency_profile": "Realtime",
        }
        focus_items = [
            {
                "source": "reddit",
                "source_label": "search:india diabetes",
                "title": "Remote Job - OpenAI - Sales Strategy & Operations - Central",
                "body": "Full time remote sales operations role with equity and compensation details.",
                "url": "https://www.reddit.com/r/jobhuntify/comments/example/job_post/",
                "published_at": "2026-05-07T00:00:00+00:00",
                "region": "Global",
                "official": False,
                "language": "en",
                "sentiment": "neutral",
                "adr_like": False,
                "entities": {},
                "tags": [],
            }
        ]

        analysis = build_project_view(snapshot, project, focus_items=focus_items)

        self.assertEqual(analysis["metrics"]["item_count"], 0)
        self.assertEqual(analysis["items"], [])

    def test_build_project_view_backfills_official_context(self) -> None:
        """Relevant official anchors should still appear even when keywords are social-first."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [
                {
                    "source": "reddit",
                    "source_label": "r/diabetes",
                    "title": "Metformin users discuss nausea",
                    "body": "People with diabetes discuss metformin side effects and blood sugar swings.",
                    "url": "https://www.reddit.com/r/diabetes/comments/example/metformin/",
                    "published_at": "2026-05-07T00:00:00+00:00",
                    "region": "Global",
                    "official": False,
                    "language": "en",
                    "sentiment": "negative",
                    "adr_like": True,
                    "entities": {
                        "drugs": ["metformin"],
                        "symptoms": ["nausea"],
                        "conditions": ["diabetes"],
                    },
                    "tags": ["ADR-like"],
                },
                {
                    "source": "nhm",
                    "source_label": "National Health Mission",
                    "title": "Training Module for Programme Managers under NP-NCD",
                    "body": "National Programme for Non-Communicable Diseases training module for program managers.",
                    "url": "https://nhm.gov.in/example/ncd-training.pdf",
                    "published_at": None,
                    "region": "India",
                    "official": True,
                    "language": "en",
                    "sentiment": "neutral",
                    "adr_like": False,
                    "entities": {},
                    "tags": ["official"],
                },
            ],
        }
        project = {
            "name": "Diabetes drugs - India vs World",
            "description": "Focus on diabetes medication and safety chatter.",
            "keywords": ["diabetes", "metformin", "blood sugar"],
            "sources": ["reddit", "nhm"],
            "latency_profile": "Realtime",
        }

        analysis = build_project_view(snapshot, project, focus_items=[])

        self.assertEqual(analysis["metrics"]["official_count"], 1)
        self.assertIn(
            "Training Module for Programme Managers under NP-NCD",
            [item["title"] for item in analysis["items"]],
        )

    def test_build_project_view_does_not_backfill_irrelevant_official_context(self) -> None:
        """Unrelated government docs should not make arbitrary searches look fake or pre-canned."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [
                {
                    "source": "nhm",
                    "source_label": "National Health Mission",
                    "title": "Training Module for Programme Managers under NP-NCD",
                    "body": "National Programme for Non-Communicable Diseases training module for program managers.",
                    "url": "https://nhm.gov.in/example/ncd-training.pdf",
                    "published_at": None,
                    "region": "India",
                    "official": True,
                    "language": "en",
                    "sentiment": "neutral",
                    "adr_like": False,
                    "entities": {},
                    "tags": ["official"],
                }
            ],
        }
        project = {
            "name": "Hair loss watch",
            "description": "Focus on hair-loss chatter and treatment discussion.",
            "keywords": ["hair loss"],
            "sources": ["nhm", "google_news", "reddit"],
            "latency_profile": "Realtime",
        }

        analysis = build_project_view(snapshot, project, focus_items=[])

        self.assertEqual(analysis["metrics"]["item_count"], 0)
        self.assertEqual(analysis["items"], [])

    def test_build_project_view_exposes_focus_queries(self) -> None:
        """The frontend should be able to explain what live searches were executed."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Dengue watch",
            "description": "Focus on dengue chatter.",
            "keywords": ["dengue", "platelet"],
            "sources": ["google_news", "reddit"],
            "latency_profile": "Realtime",
        }

        analysis = build_project_view(snapshot, project, focus_items=[])

        self.assertIn("india dengue platelet", analysis["focus_queries"])

    def test_build_project_view_rejects_partial_query_match_from_health_subreddit(self) -> None:
        """Focused search items should match the actual query terms, not just one keyword."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Metformin palpitations watch",
            "description": "Focus on direct cardiometabolic side-effect chatter.",
            "keywords": ["metformin", "palpitations"],
            "sources": ["reddit"],
            "latency_profile": "Realtime",
        }
        focus_items = [
            {
                "source": "reddit",
                "source_label": "search:metformin palpitations",
                "title": "Finally Found the Cause of my Chronic Fatigue",
                "body": "Hypoglycemia and hyperinsulinism can be missed for years. Some people online mention things like metformin or tirzepatide, but this post is about fatigue crashes.",
                "url": "https://www.reddit.com/r/cfs/comments/example/fatigue_post/",
                "published_at": "2026-05-07T00:00:00+00:00",
                "region": "Global",
                "official": False,
                "language": "en",
                "sentiment": "negative",
                "adr_like": False,
                "entities": {
                    "drugs": ["metformin", "tirzepatide"],
                    "conditions": ["hypoglycemia"],
                },
                "tags": [],
            }
        ]

        analysis = build_project_view(snapshot, project, focus_items=focus_items)

        self.assertEqual(analysis["metrics"]["item_count"], 0)
        self.assertEqual(analysis["items"], [])

    def test_build_project_view_keeps_direct_focus_query_match(self) -> None:
        """Focused search items that match both query terms should survive filtering."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Metformin palpitations watch",
            "description": "Focus on direct cardiometabolic side-effect chatter.",
            "keywords": ["metformin", "palpitations"],
            "sources": ["reddit"],
            "latency_profile": "Realtime",
        }
        focus_items = [
            {
                "source": "reddit",
                "source_label": "search:metformin palpitations",
                "title": "Metformin palpitations after dose increase",
                "body": "I started getting palpitations after increasing my metformin dose last week.",
                "url": "https://www.reddit.com/r/diabetes/comments/example/palpitations_post/",
                "published_at": "2026-05-07T00:00:00+00:00",
                "region": "India",
                "official": False,
                "language": "en",
                "sentiment": "negative",
                "adr_like": True,
                "entities": {
                    "drugs": ["metformin"],
                    "symptoms": ["palpitations"],
                    "conditions": ["diabetes"],
                },
                "tags": ["ADR-like"],
            }
        ]

        analysis = build_project_view(snapshot, project, focus_items=focus_items)

        self.assertEqual(analysis["metrics"]["item_count"], 1)
        self.assertEqual(analysis["items"][0]["title"], "Metformin palpitations after dose increase")

    def test_build_project_view_matches_brand_name_synonym(self) -> None:
        """Brand-name aliases should match a project brief keyed on the canonical drug name."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [
                {
                    "source": "reddit",
                    "source_label": "r/diabetes",
                    "title": "Glycomet is giving me nausea after meals",
                    "body": "My doctor started Glycomet for diabetes and now I feel nauseous after dinner.",
                    "url": "https://www.reddit.com/r/diabetes/comments/example/glycomet_post/",
                    "published_at": "2026-05-07T00:00:00+00:00",
                    "region": "India",
                    "official": False,
                    "language": "en",
                    "sentiment": "negative",
                    "adr_like": True,
                    "entities": {
                        "symptoms": ["nausea"],
                        "conditions": ["diabetes"],
                    },
                    "tags": ["ADR-like"],
                }
            ],
        }
        project = {
            "name": "Metformin watch",
            "description": "Focus on metformin-related complaints.",
            "keywords": ["metformin"],
            "sources": ["reddit"],
            "latency_profile": "Realtime",
        }

        analysis = build_project_view(snapshot, project, focus_items=[])

        self.assertEqual(analysis["metrics"]["item_count"], 1)
        self.assertEqual(analysis["items"][0]["title"], "Glycomet is giving me nausea after meals")

    def test_build_project_view_keeps_symptom_synonym_focus_result(self) -> None:
        """Symptom aliases should survive focused search filtering for plain-language briefs."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Nose bleeding watch",
            "description": "Focus on nose-bleeding chatter and public-health references.",
            "keywords": ["nose bleeding"],
            "sources": ["google_news"],
            "latency_profile": "Realtime",
        }
        focus_items = [
            {
                "source": "google_news",
                "source_label": "Google News RSS:india nosebleed",
                "title": "Doctors report more nosebleed complaints during the heatwave",
                "body": "Delhi clinics are seeing more nosebleed complaints and advising hydration during summer heat.",
                "url": "https://news.google.com/example/nosebleed-story",
                "published_at": "2026-05-07T00:00:00+00:00",
                "region": "India",
                "official": False,
                "language": "en",
                "sentiment": "neutral",
                "adr_like": False,
                "entities": {
                    "symptoms": ["nosebleed"],
                },
                "tags": [],
            }
        ]

        analysis = build_project_view(snapshot, project, focus_items=focus_items)

        self.assertIn("india nosebleed", analysis["focus_queries"])
        self.assertEqual(analysis["metrics"]["item_count"], 1)
        self.assertEqual(
            analysis["items"][0]["title"],
            "Doctors report more nosebleed complaints during the heatwave",
        )

    def test_build_project_view_rejects_scattered_focus_query_mentions(self) -> None:
        """Focused search items should not pass when query terms only appear in unrelated sentences."""

        snapshot = {
            "generated_at": "2026-05-07T00:00:00+00:00",
            "items": [],
        }
        project = {
            "name": "Metformin palpitations watch",
            "description": "Focus on direct cardiometabolic side-effect chatter.",
            "keywords": ["metformin", "palpitations"],
            "sources": ["reddit"],
            "latency_profile": "Realtime",
        }
        focus_items = [
            {
                "source": "reddit",
                "source_label": "search:metformin palpitations",
                "title": "Finally Found the Cause of my Chronic Fatigue, and it was not what I Expected!",
                "body": "Some people said things like metformin or tirzepatide. Signs and symptoms can include dizziness, fatigue, and palpitations. This post is about chronic fatigue and hypoglycemia.",
                "url": "https://www.reddit.com/r/chronicfatigue/comments/example/fatigue_post/",
                "published_at": "2026-05-07T00:00:00+00:00",
                "region": "Global",
                "official": False,
                "language": "en",
                "sentiment": "negative",
                "adr_like": True,
                "entities": {
                    "drugs": ["metformin", "tirzepatide"],
                    "symptoms": ["dizziness", "fatigue", "palpitations"],
                    "conditions": ["hypoglycemia"],
                },
                "tags": ["ADR-like"],
            }
        ]

        analysis = build_project_view(snapshot, project, focus_items=focus_items)

        self.assertEqual(analysis["metrics"]["item_count"], 0)
        self.assertEqual(analysis["items"], [])


if __name__ == "__main__":
    unittest.main()