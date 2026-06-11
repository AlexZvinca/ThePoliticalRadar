from __future__ import annotations

import email.utils
from datetime import datetime, timezone
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from app.config import Settings
from app.domain import AnalysisRequest, SourceItem, SourceName


async def fetch_news_items(request: AnalysisRequest, settings: Settings) -> list[SourceItem]:
    query = quote_plus(f'"{request.entity}" {request.country} politics')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    async with httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        headers={"User-Agent": settings.http_user_agent},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    items: list[SourceItem] = []
    for entry in root.findall("./channel/item"):
        title = _text(entry, "title")
        description = _text(entry, "description")
        link = _text(entry, "link")
        published_at = _parse_rss_date(_text(entry, "pubDate"))
        if not title or not (request.start_date <= published_at.date() <= request.end_date):
            continue
        source_label = _source_label(entry)
        items.append(
            SourceItem(
                source=SourceName.news,
                text=" ".join(part for part in [title, description] if part),
                published_at=published_at,
                title=title,
                author=source_label,
                url=link,
                metadata={"provider": "google_news_rss", "source": source_label},
            )
        )
        if len(items) >= request.limit_per_source:
            break
    return items


def _text(entry: ElementTree.Element, tag: str) -> str:
    value = entry.findtext(tag)
    return value.strip() if value else ""


def _source_label(entry: ElementTree.Element) -> str | None:
    for child in entry:
        if child.tag.endswith("source") and child.text:
            return child.text.strip()
    return None


def _parse_rss_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = email.utils.parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
