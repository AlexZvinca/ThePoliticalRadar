from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain import SourceItem, SourceName


def build_demo_items(entity: str, country: str, limit: int) -> list[SourceItem]:
    now = datetime.now(timezone.utc)
    templates = [
        ("I think {entity} finally showed responsible leadership in {country}.", "civic_forum"),
        ("The latest decision from {entity} looks like another weak failure.", "policy_watch"),
        ("People are still neutral, but the debate around {entity} is getting louder.", "daily_thread"),
        ("Supporters say {entity} brought progress and stability.", "townhall"),
        ("Critics call the announcement a scandal and say trust is falling.", "news_comments"),
        ("The campaign around {entity} feels transparent and credible to me.", "analysis_room"),
        ("Many voters are angry about the bad communication from {entity}.", "local_politics"),
        ("The discussion is mixed: good goals, but worse execution.", "election_watch"),
        ("Some users praise the strong economic message from {entity}.", "public_square"),
        ("Others say the party is corrupt and incompetent.", "debate_hub"),
    ]
    items: list[SourceItem] = []
    for index in range(limit):
        template, author = templates[index % len(templates)]
        items.append(
            SourceItem(
                source=SourceName.csv,
                text=template.format(entity=entity, country=country),
                published_at=now - timedelta(days=index % 14),
                author=author,
                title=f"Demo public reaction {index + 1}",
                url=f"https://example.com/the-political-radar/demo/{index + 1}",
                metadata={"demo": True, "country": country},
            )
        )
    return items
