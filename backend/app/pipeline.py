from __future__ import annotations

import asyncio

from app.aggregates import build_aggregates
from app.config import Settings
from app.connectors.demo_data import build_demo_items
from app.connectors.news import fetch_news_items
from app.connectors.wikipedia import fetch_wikipedia_profile
from app.connectors.youtube import fetch_youtube_items
from app.domain import Analysis, AnalysisStatus, EventAnnotation, SourceItem, SourceName
from app.http_utils import describe_http_error
from app.sentiment import SentimentAnalyzer
from app.utils import deduplicate_items


async def run_analysis(analysis: Analysis, settings: Settings) -> Analysis:
    analysis.status = AnalysisStatus.running
    analysis.touch()
    try:
        analysis.profile, profile_warning = await safe_fetch_profile(analysis, settings)
        items, events, warnings = await collect_items(analysis, settings)
        if profile_warning:
            warnings.insert(0, profile_warning)
        analysis.warnings = warnings
        items = deduplicate_items(items)
        sentiments = await SentimentAnalyzer(settings).analyze(
            items,
            analysis.request.language,
            analysis.request.entity,
        )
        analysis.items = items
        analysis.sentiments = sentiments
        analysis.aggregates = build_aggregates(items, sentiments, events)
        analysis.status = AnalysisStatus.completed
    except Exception as exc:
        analysis.status = AnalysisStatus.failed
        analysis.error = str(exc)
    analysis.touch()
    return analysis


async def safe_fetch_profile(analysis: Analysis, settings: Settings):
    try:
        return await fetch_wikipedia_profile(analysis.request, settings), None
    except Exception as exc:
        return None, f"wikipedia profile lookup failed: {describe_http_error(exc)}."


async def collect_items(
    analysis: Analysis,
    settings: Settings,
) -> tuple[list[SourceItem], list[EventAnnotation], list[str]]:
    request = analysis.request
    tasks = []
    if SourceName.news in request.sources:
        tasks.append((SourceName.news, fetch_news_items(request, settings)))
    if SourceName.youtube in request.sources:
        tasks.append((SourceName.youtube, fetch_youtube_items(request, settings)))

    items: list[SourceItem] = []
    events: list[EventAnnotation] = []
    warnings: list[str] = []
    if tasks:
        source_names = [source for source, _ in tasks]
        results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                warnings.append(f"{source_name.value} could not be reached: {describe_http_error(result)}.")
                continue
            if isinstance(result, tuple):
                source_items, source_events = result
                items.extend(source_items)
                events.extend(source_events)
                if not source_items:
                    warnings.append(f"{source_name.value} returned no matching items for this query/date range.")
            else:
                items.extend(result)
                if not result:
                    warnings.append(f"{source_name.value} returned no matching items for this query/date range.")
    if SourceName.csv in request.sources:
        items.extend(build_demo_items(request.entity, request.country, min(request.limit_per_source, 24)))
    elif not items:
        warnings.append("No online source returned analyzable text. Select CSV for deterministic demo data.")
    return items, events, warnings
