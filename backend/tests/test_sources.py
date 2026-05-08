"""Parser regression tests for source connectors."""

from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from app.config import AppConfig
from app.models import ContentItem
from app.sources.google_news import GoogleNewsSource
from app.sources.telegram import _body_to_title, _parse_channel_messages
from app.sources.youtube import _enrich_watch_page_items, _parse_feed_items, _parse_search_results


class SourceParserTests(unittest.TestCase):
    """Keep connector parsing deterministic without live network dependencies."""

    def test_parse_youtube_feed_items_extracts_video_data(self) -> None:
        """YouTube Atom feeds should become normalized content items."""

        xml_text = """<?xml version='1.0' encoding='UTF-8'?>
        <feed xmlns='http://www.w3.org/2005/Atom' xmlns:media='http://search.yahoo.com/mrss/'>
          <entry>
            <title>Diabetes Warning Signs</title>
            <link rel='alternate' href='https://www.youtube.com/watch?v=abc123' />
            <published>2026-05-07T10:00:00+00:00</published>
            <media:group>
              <media:description>Doctors explain early diabetes symptoms and blood sugar warning signs.</media:description>
            </media:group>
          </entry>
        </feed>"""

        items = _parse_feed_items(xml_text, "WHO", set(), limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "youtube")
        self.assertEqual(items[0].source_label, "YouTube: WHO")
        self.assertEqual(items[0].title, "Diabetes Warning Signs")
        self.assertIn("blood sugar", items[0].body)

    def test_parse_telegram_channel_messages_extracts_permalink_and_body(self) -> None:
        """Telegram /s/ pages should yield normalized message items."""

        html = """
        <div class="tgme_widget_message_wrap js-widget_message_wrap">
          <div>
            <a class="tgme_widget_message_date" href="https://t.me/MyGovIndia/42"><time datetime="2026-05-07T08:30:00+00:00"></time></a>
            <div class="tgme_widget_message_text js-message_text" dir="auto">
              Health camp in Delhi today.<br/>Free blood pressure and sugar screening available.
            </div>
          </div>
        </div>
        """

        items = _parse_channel_messages(html, "MyGov India", set(), limit=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "telegram")
        self.assertEqual(items[0].source_label, "Telegram: MyGov India")
        self.assertEqual(items[0].url, "https://t.me/MyGovIndia/42")
        self.assertIn("blood pressure", items[0].body)
        self.assertEqual(items[0].title, "Health camp in Delhi today")

    def test_parse_youtube_search_results_extracts_query_focused_video(self) -> None:
        """YouTube public search HTML should yield topic-specific video items."""

        html = """
        <html><body><script>
        var ytInitialData = {
          "contents": {
            "twoColumnSearchResultsRenderer": {
              "primaryContents": {
                "sectionListRenderer": {
                  "contents": [
                    {
                      "itemSectionRenderer": {
                        "contents": [
                          {
                            "videoRenderer": {
                              "videoId": "abc123",
                              "title": {"runs": [{"text": "Diabetes symptoms explained"}]},
                              "ownerText": {"runs": [{"text": "WHO"}]},
                              "descriptionSnippet": {"runs": [{"text": "Doctors explain blood sugar warning signs and treatment steps."}]}
                            }
                          }
                        ]
                      }
                    }
                  ]
                }
              }
            }
          }
        };</script></body></html>
        """

        items = _parse_search_results(html, "diabetes", set(), limit=3)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "youtube")
        self.assertEqual(items[0].source_label, "YouTube Search: diabetes · WHO")
        self.assertEqual(items[0].url, "https://www.youtube.com/watch?v=abc123")
        self.assertIn("blood sugar", items[0].body)

    @patch("app.sources.google_news.fetch_text")
    def test_google_news_fetch_uses_publisher_in_labels_and_thin_body_fallback(self, fetch_text_mock) -> None:
        """Google News items should expose the publisher when RSS blurbs are only title plus source."""

        fetch_text_mock.return_value = """<?xml version='1.0' encoding='UTF-8'?>
        <rss><channel>
          <item>
            <title>Diabetes Drug Metformin Could Reduce Insulin Needs</title>
            <link>https://news.google.com/rss/articles/test-article</link>
            <description><![CDATA[
              <a href="https://news.google.com/rss/articles/test-article">Diabetes Drug Metformin Could Reduce Insulin Needs</a>&nbsp;&nbsp;<font color="#6f6f6f">NDTV</font>
            ]]></description>
            <source url="https://www.ndtv.com">NDTV</source>
            <pubDate>Fri, 08 May 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
        config = replace(AppConfig(), news_search_queries=("diabetes",), max_items_per_source=2)

        items = GoogleNewsSource().fetch(config)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_label, "Google News RSS: diabetes · NDTV")
        self.assertEqual(
            items[0].body,
            "Diabetes Drug Metformin Could Reduce Insulin Needs Reported by NDTV via Google News.",
        )

    @patch("app.sources.youtube.fetch_text")
    def test_enrich_watch_page_items_uses_watch_page_description_for_thin_feed_items(
        self,
        fetch_text_mock,
    ) -> None:
        """Thin YouTube feed snippets should be upgraded from the watch page description."""

        fetch_text_mock.return_value = """
        <html>
          <head>
            <meta property="og:description" content="Short backup description" />
          </head>
          <body>
            <script>
              var ytInitialPlayerResponse = {"videoDetails":{"shortDescription":"Detailed diabetes explainer with palpitations, nausea, and treatment guidance from clinicians."}};
            </script>
          </body>
        </html>
        """
        items = [
            ContentItem(
                source="youtube",
                source_label="YouTube: WHO",
                title="Diabetes explainer",
                body="Short teaser",
                url="https://www.youtube.com/watch?v=abc123",
                published_at="2026-05-07T10:00:00+00:00",
            )
        ]

        enriched = _enrich_watch_page_items(items, AppConfig())

        self.assertEqual(len(enriched), 1)
        self.assertIn("treatment guidance", enriched[0].body)
        self.assertGreater(len(enriched[0].body), len(items[0].body))

    def test_body_to_title_trims_long_messages(self) -> None:
        """Telegram title generation should stay compact for long messages."""

        body = (
            "This is a long public advisory message that should be shortened into a compact title "
            "without dragging the entire Telegram post into the headline."
        )

        title = _body_to_title(body)

        self.assertTrue(title.endswith("..."))
        self.assertLessEqual(len(title.split()), 16)


if __name__ == "__main__":
    unittest.main()