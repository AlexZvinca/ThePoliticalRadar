from __future__ import annotations

from collections import Counter, defaultdict

from app.domain import (
    AggregateSnapshot,
    DailySentimentPoint,
    EventAnnotation,
    Peak,
    SentimentLabel,
    SentimentResult,
    SourceItem,
    SourceName,
)


def build_aggregates(
    items: list[SourceItem],
    sentiments: list[SentimentResult],
    events: list[EventAnnotation],
) -> AggregateSnapshot:
    sentiment_by_item = {sentiment.item_id: sentiment for sentiment in sentiments}
    distribution: Counter[SentimentLabel] = Counter()
    source_distribution: Counter[SourceName] = Counter()
    daily_buckets: dict[str, Counter[SentimentLabel]] = defaultdict(Counter)
    score_buckets: dict[str, list[float]] = defaultdict(list)
    phrase_counter: Counter[str] = Counter()
    representatives: dict[SentimentLabel, list[SourceItem]] = {
        SentimentLabel.positive: [],
        SentimentLabel.neutral: [],
        SentimentLabel.negative: [],
        SentimentLabel.mixed: [],
    }

    for item in items:
        sentiment = sentiment_by_item.get(item.id)
        if not sentiment:
            continue
        distribution[sentiment.label] += 1
        source_distribution[item.source] += 1
        date_key = item.published_at.date().isoformat()
        daily_buckets[date_key][sentiment.label] += 1
        score_buckets[date_key].append(sentiment.scores.positive - sentiment.scores.negative)
        phrase_counter.update(sentiment.key_phrases)
        if item.source == SourceName.youtube and len(representatives[sentiment.label]) < 4:
            representatives[sentiment.label].append(item)

    if not events:
        events = [
            EventAnnotation(
                date=item.published_at.date(),
                title=item.title or item.text[:120],
                source=str(item.author or "News RSS"),
                url=item.url,
            )
            for item in items
            if item.source == SourceName.news
        ][:10]

    daily: list[DailySentimentPoint] = []
    for date_key, bucket in sorted(daily_buckets.items()):
        volume = sum(bucket.values())
        scores = score_buckets[date_key]
        daily.append(
            DailySentimentPoint(
                date=date_key,
                positive=bucket[SentimentLabel.positive],
                neutral=bucket[SentimentLabel.neutral],
                negative=bucket[SentimentLabel.negative],
                mixed=bucket[SentimentLabel.mixed],
                average_score=round(sum(scores) / len(scores), 3) if scores else 0.0,
                volume=volume,
            )
        )

    peaks = detect_peaks(daily)
    return AggregateSnapshot(
        total_items=len(sentiments),
        sentiment_distribution={label: distribution[label] for label in SentimentLabel},
        source_distribution={source: source_distribution[source] for source in SourceName},
        daily=daily,
        peaks=peaks,
        key_phrases=phrase_counter.most_common(20),
        representatives=representatives,
        events=events[:10],
    )


def detect_peaks(daily: list[DailySentimentPoint]) -> list[Peak]:
    if not daily:
        return []
    average_volume = sum(point.volume for point in daily) / len(daily)
    peaks: list[Peak] = []
    for point in daily:
        negative_share = point.negative / point.volume if point.volume else 0
        if point.volume >= max(3, average_volume * 1.35) or negative_share >= 0.6:
            peaks.append(
                Peak(
                    date=point.date,
                    volume=point.volume,
                    negative_share=round(negative_share, 3),
                    note="High attention or unusually negative discussion detected.",
                )
            )
    return peaks[:6]
