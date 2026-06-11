import unittest
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.connectors.news import fetch_news_items
from app.domain import AnalysisRequest, SourceName


class FakeResponse:
    text = """<?xml version="1.0" encoding="UTF-8"?>
    <rss><channel>
      <item>
        <title>USR announces political decision</title>
        <description>Romania politics update</description>
        <link>https://example.com/news</link>
        <pubDate>Wed, 10 Jun 2026 10:00:00 GMT</pubDate>
        <source>Example News</source>
      </item>
    </channel></rss>
    """

    def raise_for_status(self):
        return None


class NewsConnectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_news_items_parses_rss_entries(self):
        request = AnalysisRequest(
            entity="USR",
            country="Romania",
            start_date="2026-06-01",
            end_date="2026-06-11",
            sources=[SourceName.news],
        )
        fake_client = AsyncMock()
        fake_client.get.return_value = FakeResponse()

        with patch("app.connectors.news.httpx.AsyncClient") as client_class:
            client_class.return_value.__aenter__.return_value = fake_client
            items = await fetch_news_items(request, Settings())

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, SourceName.news)
        self.assertIn("USR announces", items[0].text)


if __name__ == "__main__":
    unittest.main()
