import unittest
from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.connectors.wikipedia import _profile_score, fetch_wikipedia_profile
from app.domain import AnalysisRequest, SourceName


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class WikipediaConnectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_wikipedia_profile_returns_thumbnail_and_page_url(self):
        request = AnalysisRequest(
            entity="USR",
            country="Romania",
            start_date="2026-01-01",
            end_date="2026-01-02",
            sources=[SourceName.csv],
        )

        fake_client = AsyncMock()
        fake_client.get.side_effect = [
            FakeResponse(
                {
                    "query": {
                        "search": [
                            {"title": "Unrelated Search Result"},
                            {"title": "Save Romania Union"},
                        ]
                    }
                }
            ),
            FakeResponse(
                {
                    "title": "Unrelated Search Result",
                    "description": "software acronym",
                    "extract": "USR is a technical abbreviation.",
                }
            ),
            FakeResponse(
                {
                    "title": "Save Romania Union",
                    "description": "political party in Romania",
                    "extract": "Save Romania Union is a political party.",
                    "thumbnail": {"source": "https://example.com/usr.png"},
                    "content_urls": {"desktop": {"page": "https://example.com/usr"}},
                }
            ),
        ]

        with (
            patch("app.connectors.wikipedia.httpx.AsyncClient") as client_class,
            patch("app.connectors.wikipedia._search_queries", return_value=["USR Romania"]),
            patch("app.connectors.wikipedia._candidate_languages", return_value=["en"]),
        ):
            client_class.return_value.__aenter__.return_value = fake_client
            profile = await fetch_wikipedia_profile(request, Settings())

        self.assertIsNotNone(profile)
        self.assertEqual(profile.title, "Save Romania Union")
        self.assertEqual(str(profile.image_url), "https://example.com/usr.png")

    def test_profile_score_prefers_political_candidate(self):
        request = AnalysisRequest(
            entity="Eugen Tomac",
            country="Romania",
            start_date="2026-01-01",
            end_date="2026-01-02",
            sources=[SourceName.csv],
        )
        wrong = {"title": "Eugen", "description": "given name", "extract": "Eugen is a name."}
        right = {
            "title": "Eugen Tomac",
            "description": "Romanian politician",
            "extract": "Eugen Tomac is a Romanian politician and member of parliament.",
        }

        self.assertGreater(_profile_score(right, request), _profile_score(wrong, request))


if __name__ == "__main__":
    unittest.main()
