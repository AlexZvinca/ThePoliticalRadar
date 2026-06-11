from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.domain import AnalysisRequest, SourceItem, SourceName


async def fetch_youtube_items(request: AnalysisRequest, settings: Settings) -> list[SourceItem]:
    if not settings.youtube_api_key:
        return []

    query = f"{request.entity} {request.country} politics"
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        search_response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "id,snippet",
                "q": query,
                "type": "video",
                "maxResults": 5,
                "key": settings.youtube_api_key,
                "publishedAfter": f"{request.start_date.isoformat()}T00:00:00Z",
                "publishedBefore": f"{request.end_date.isoformat()}T23:59:59Z",
            },
        )
        search_response.raise_for_status()
        video_ids = [
            item["id"]["videoId"]
            for item in search_response.json().get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        items: list[SourceItem] = []
        for video_id in video_ids:
            comments_response = await client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(request.limit_per_source, 50),
                    "textFormat": "plainText",
                    "key": settings.youtube_api_key,
                },
            )
            comments_response.raise_for_status()
            for comment in comments_response.json().get("items", []):
                snippet = comment["snippet"]["topLevelComment"]["snippet"]
                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                items.append(
                    SourceItem(
                        source=SourceName.youtube,
                        text=snippet["textDisplay"],
                        published_at=published_at,
                        author=None,
                        url=f"https://www.youtube.com/watch?v={video_id}&lc={comment.get('id', '')}",
                        metadata={"video_id": video_id, "like_count": snippet.get("likeCount", 0)},
                    )
                )
    return items
