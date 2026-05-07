"""Parser regression tests for source connectors."""

from __future__ import annotations

import unittest

from app.sources.telegram import _body_to_title, _parse_channel_messages
from app.sources.youtube import _parse_feed_items


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