from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO

from app.domain import SourceItem, SourceName


def parse_csv_items(content: str) -> list[SourceItem]:
    reader = csv.DictReader(StringIO(content))
    items: list[SourceItem] = []
    for row in reader:
        text = row.get("text") or row.get("comment") or row.get("body") or ""
        if not text.strip():
            continue
        published_at = _parse_date(row.get("date") or row.get("published_at"))
        source_value = (row.get("source") or "csv").strip().lower()
        source = SourceName(source_value) if source_value in SourceName._value2member_map_ else SourceName.csv
        items.append(
            SourceItem(
                source=source,
                text=text,
                published_at=published_at,
                author=row.get("author") or row.get("source_label"),
                title=row.get("title"),
                url=row.get("url") or None,
                metadata={"uploaded": True},
            )
        )
    return items


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

