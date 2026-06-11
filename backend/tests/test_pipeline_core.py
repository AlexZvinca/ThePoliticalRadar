import unittest
from datetime import datetime, timezone

from app.aggregates import build_aggregates, detect_peaks
from app.connectors.csv_connector import parse_csv_items
from app.domain import (
    Analysis,
    AnalysisRequest,
    DailySentimentPoint,
    SentimentLabel,
    SentimentResult,
    SentimentScores,
    SourceItem,
    SourceName,
)
from app.pipeline import run_analysis
from app.sentiment import SentimentAnalyzer
from app.config import Settings
from app.utils import MAX_RETAINED_TEXT_CHARS, deduplicate_items


class PipelineCoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_sentiment_detects_negative_text(self):
        item = SourceItem(
            source=SourceName.csv,
            text="This is a corrupt scandal and a terrible failure.",
            published_at=datetime.now(timezone.utc),
        )

        results = await SentimentAnalyzer(Settings()).analyze([item], "en", "Example Party")

        self.assertEqual(results[0].label, SentimentLabel.negative)
        self.assertGreater(results[0].scores.negative, results[0].scores.positive)

    def test_deduplicate_items_removes_repeated_text(self):
        now = datetime.now(timezone.utc)
        items = [
            SourceItem(source=SourceName.csv, text="Same political comment", published_at=now),
            SourceItem(source=SourceName.csv, text="same political comment", published_at=now),
        ]

        self.assertEqual(len(deduplicate_items(items)), 1)

    def test_text_retention_is_limited_to_short_excerpt(self):
        now = datetime.now(timezone.utc)
        items = [
            SourceItem(source=SourceName.csv, text="A" * 1200, published_at=now),
        ]

        retained = deduplicate_items(items)

        self.assertLessEqual(len(retained[0].text), MAX_RETAINED_TEXT_CHARS)
        self.assertTrue(retained[0].text.endswith("..."))

    def test_csv_parser_accepts_expected_columns(self):
        content = "text,source,date,author,url\nGreat progress,csv,2026-01-01,analyst,https://example.com\n"

        items = parse_csv_items(content)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, SourceName.csv)

    def test_aggregates_include_distribution_and_key_phrases(self):
        now = datetime.now(timezone.utc)
        item = SourceItem(source=SourceName.csv, text="Great transparent progress", published_at=now)
        sentiment = SentimentResult(
            item_id=item.id,
            label=SentimentLabel.positive,
            scores=SentimentScores(positive=0.8, neutral=0.1, negative=0.1),
            key_phrases=["transparent", "progress"],
        )

        snapshot = build_aggregates([item], [sentiment], [])

        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.sentiment_distribution[SentimentLabel.positive], 1)
        self.assertEqual(snapshot.key_phrases[0], ("transparent", 1))

    def test_peak_detection_flags_high_negative_share(self):
        peaks = detect_peaks(
            [
                DailySentimentPoint(date="2026-01-01", volume=5, negative=4),
                DailySentimentPoint(date="2026-01-02", volume=5, positive=4),
            ]
        )

        self.assertEqual(len(peaks), 1)
        self.assertEqual(str(peaks[0].date), "2026-01-01")

    def test_analysis_request_rejects_more_than_three_years(self):
        with self.assertRaises(ValueError):
            AnalysisRequest(
                entity="Example Party",
                country="Romania",
                start_date="2020-01-01",
                end_date="2024-01-02",
                sources=[SourceName.news],
            )

    async def test_online_failure_without_csv_does_not_use_demo_data(self):
        analysis = Analysis(
            request=AnalysisRequest(
                entity="USR",
                country="Romania",
                start_date="2026-05-27",
                end_date="2026-06-10",
                sources=[SourceName.news],
                language="ro",
                limit_per_source=25,
            )
        )

        with unittest.mock.patch("app.pipeline.fetch_news_items", side_effect=RuntimeError("offline")):
            completed = await run_analysis(analysis, Settings())

        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.aggregates.total_items, 0)
        self.assertTrue(completed.warnings)


if __name__ == "__main__":
    unittest.main()
