"""Unit tests for the stdlib ingestion pipeline."""

from __future__ import annotations

import unittest

from app.models import ContentItem
from app.pipeline import build_signals, enrich_item, mask_pii


class PipelineTests(unittest.TestCase):
    """Validate the lowest-cost critical paths before API work."""

    def test_mask_pii_redacts_phone_and_email(self) -> None:
        """PII masking should remove obvious contact details."""

        masked = mask_pii("Call +91 9876543210 or mail user@example.com")
        self.assertNotIn("9876543210", masked)
        self.assertNotIn("user@example.com", masked)
        self.assertIn("[phone]", masked)
        self.assertIn("[email]", masked)

    def test_enrich_item_detects_entities(self) -> None:
        """Entity extraction should identify relevant health terms."""

        item = ContentItem(
            source="reddit",
            source_label="r/india",
            title="Metformin users report palpitations in Delhi",
            body="Several diabetes patients describe chest pain after taking it.",
            url="https://example.com",
            published_at=None,
        )
        enriched = enrich_item(item)
        self.assertIn("metformin", enriched.entities["drugs"])
        self.assertIn("palpitations", enriched.entities["symptoms"])
        self.assertEqual(enriched.region, "Delhi")
        self.assertTrue(enriched.adr_like)

    def test_enrich_item_canonicalizes_symptom_aliases(self) -> None:
        """Symptom alias variants should collapse into one canonical entity."""

        item = ContentItem(
            source="google_news",
            source_label="Google News RSS: india nosebleed",
            title="Why nosebleeds spike in summer",
            body="Doctors explain why nose bleeds become more common in dry heat.",
            url="https://example.com/nosebleed",
            published_at=None,
        )

        enriched = enrich_item(item)

        self.assertEqual(enriched.entities["symptoms"], ["nose bleeding"])

    def test_enrich_item_canonicalizes_chest_pain_aliases(self) -> None:
        """Chest-pain variants should collapse into one canonical symptom for scoring."""

        item = ContentItem(
            source="google_news",
            source_label="Google News RSS: india angina",
            title="Doctors explain when chest tightness needs urgent evaluation",
            body="Common angina symptoms can look different across patients.",
            url="https://example.com/chest-pain",
            published_at=None,
        )

        enriched = enrich_item(item)

        self.assertEqual(enriched.entities["symptoms"], ["chest pain"])

    def test_build_signals_scores_cross_source_evidence(self) -> None:
        """Signals should be emitted when two sources corroborate the same pair."""

        items = [
            enrich_item(
                ContentItem(
                    source="reddit",
                    source_label="r/india",
                    title="Semaglutide users mention nausea",
                    body="People in India are discussing side effect concerns.",
                    url="https://example.com/1",
                    published_at=None,
                )
            ),
            enrich_item(
                ContentItem(
                    source="cdsco",
                    source_label="CDSCO",
                    title="Drug safety alert for semaglutide quality concerns",
                    body="Official advisory on diabetes drug safety.",
                    url="https://example.com/2",
                    published_at=None,
                    official=True,
                )
            ),
        ]
        signals = build_signals(items)
        self.assertTrue(signals)
        self.assertGreaterEqual(signals[0].confidence, 50)

    def test_build_signals_emits_symptom_only_cluster(self) -> None:
        """Symptom-only focused hits should still produce a readable signal card."""

        items = [
            enrich_item(
                ContentItem(
                    source="google_news",
                    source_label="Google News RSS: india hair loss",
                    title="New Plant-Based Serum Shows Promise in Hair Loss Treatment",
                    body="India clinics are seeing more demand for hair loss care and treatment options.",
                    url="https://example.com/hair-loss",
                    published_at=None,
                )
            )
        ]

        signals = build_signals(items)

        self.assertTrue(signals)
        self.assertEqual(signals[0].title, "Hair Loss concern cluster")

    def test_build_signals_falls_back_to_focus_label_when_entities_are_missing(self) -> None:
        """Focused search hits should still summarize when extraction misses the topic phrase."""

        items = [
            ContentItem(
                source="google_news",
                source_label="Google News RSS: india dry mouth",
                title="Specialists discuss better hydration plans this summer",
                body="Treatment roundups and patient advice are getting more attention.",
                url="https://example.com/dry-mouth",
                published_at=None,
            )
        ]

        signals = build_signals(items)

        self.assertTrue(signals)
        self.assertEqual(signals[0].title, "Dry Mouth concern cluster")

    def test_enrich_item_avoids_false_health_matches(self) -> None:
        """Non-health text should not trigger accidental entity matches."""

        item = ContentItem(
            source="reddit",
            source_label="search:india diabetes",
            title="Remote Job - OpenAI - Sales Strategy & Operations - Central",
            body="Full time remote sales operations role with compensation details and equity.",
            url="https://example.com/job",
            published_at=None,
        )
        enriched = enrich_item(item)
        self.assertEqual(enriched.entities, {})
        self.assertFalse(enriched.adr_like)

    def test_enrich_item_strips_markdown_formatting(self) -> None:
        """Markdown-heavy Reddit text should be flattened before display and matching."""

        item = ContentItem(
            source="reddit",
            source_label="search:india metformin",
            title="**Metformin** update",
            body="**TL;DR** [Eli Lilly](https://example.com) reports \\~24% weight loss.\n- nausea\n- vomiting",
            url="https://example.com/post",
            published_at=None,
        )
        enriched = enrich_item(item)
        self.assertEqual(enriched.title, "Metformin update")
        self.assertIn("Eli Lilly", enriched.body)
        self.assertIn("~24%", enriched.body)
        self.assertNotIn("**", enriched.body)
        self.assertNotIn("[Eli Lilly](https://example.com)", enriched.body)


if __name__ == "__main__":
    unittest.main()