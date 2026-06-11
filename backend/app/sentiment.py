from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.domain import SentimentLabel, SentimentResult, SentimentScores, SourceItem
from app.utils import extract_key_phrases

POSITIVE_WORDS = {
    "accountable",
    "better",
    "credible",
    "effective",
    "fair",
    "good",
    "great",
    "honest",
    "improved",
    "progress",
    "responsible",
    "stable",
    "strong",
    "support",
    "transparent",
    "trust",
    "win",
}

NEGATIVE_WORDS = {
    "angry",
    "bad",
    "chaos",
    "corrupt",
    "crisis",
    "failed",
    "failure",
    "fraud",
    "incompetent",
    "lies",
    "negative",
    "scandal",
    "weak",
    "worse",
    "worst",
}


class SentimentAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def analyze(self, items: list[SourceItem], language: str, entity: str) -> list[SentimentResult]:
        if self.settings.azure_language_endpoint and self.settings.azure_language_key:
            try:
                return await self._analyze_with_azure(items, language, entity)
            except (httpx.HTTPError, KeyError, ValueError):
                pass
        return [self._analyze_locally(item, entity) for item in items]

    async def check_azure_connection(self) -> dict[str, str | bool]:
        if not self.settings.azure_language_endpoint or not self.settings.azure_language_key:
            return {
                "configured": False,
                "ok": False,
                "mode": "local-fallback",
                "message": "Azure AI Language endpoint/key are not configured.",
            }

        probe = SourceItem(
            source="csv",
            text="This is a good connectivity test for Azure sentiment analysis.",
            published_at=datetime.now(timezone.utc),
        )
        try:
            result = await self._analyze_with_azure([probe], "en", "Azure test")
        except httpx.HTTPStatusError as exc:
            return {
                "configured": True,
                "ok": False,
                "mode": "azure",
                "message": f"Azure returned HTTP {exc.response.status_code}. Check endpoint, key, region, and quota.",
            }
        except httpx.HTTPError as exc:
            return {
                "configured": True,
                "ok": False,
                "mode": "azure",
                "message": f"Could not reach Azure AI Language: {exc.__class__.__name__}.",
            }
        except (KeyError, ValueError) as exc:
            return {
                "configured": True,
                "ok": False,
                "mode": "azure",
                "message": f"Unexpected Azure response format: {exc.__class__.__name__}.",
            }

        return {
            "configured": True,
            "ok": True,
            "mode": "azure",
            "message": f"Azure AI Language responded successfully with {result[0].label} sentiment.",
        }

    async def _analyze_with_azure(
        self,
        items: list[SourceItem],
        language: str,
        entity: str,
    ) -> list[SentimentResult]:
        endpoint = self.settings.azure_language_endpoint.rstrip("/")
        url = f"{endpoint}/language/:analyze-text?api-version=2023-04-01"
        headers = {
            "Ocp-Apim-Subscription-Key": self.settings.azure_language_key or "",
            "Content-Type": "application/json",
        }
        results: list[SentimentResult] = []
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            for offset in range(0, len(items), 10):
                batch = items[offset : offset + 10]
                documents = []
                for item in batch:
                    document = {"id": item.id, "text": item.text}
                    if language.lower() != "auto":
                        document["language"] = language
                    documents.append(document)

                payload = {
                    "kind": "SentimentAnalysis",
                    "parameters": {"opinionMining": True},
                    "analysisInput": {"documents": documents},
                }
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                azure_results = response.json()["results"]
                documents = azure_results.get("documents", [])
                errors = azure_results.get("errors", [])
                if errors:
                    raise ValueError(errors[0].get("error", {}).get("message", "Azure document error"))
                for document in documents:
                    scores = document["confidenceScores"]
                    results.append(
                        SentimentResult(
                            item_id=document["id"],
                            label=SentimentLabel(document["sentiment"]),
                            scores=SentimentScores(**scores),
                            key_phrases=extract_key_phrases(
                                next(item.text for item in batch if item.id == document["id"]),
                                entity,
                            ),
                        )
                    )
        return results

    def _analyze_locally(self, item: SourceItem, entity: str) -> SentimentResult:
        words = {part.strip(".,!?;:()[]{}\"'").casefold() for part in item.text.split()}
        positive_hits = len(words & POSITIVE_WORDS)
        negative_hits = len(words & NEGATIVE_WORDS)
        if positive_hits > negative_hits:
            label = SentimentLabel.positive
            positive = min(0.9, 0.55 + positive_hits * 0.12)
            negative = max(0.05, 0.25 - positive_hits * 0.04)
        elif negative_hits > positive_hits:
            label = SentimentLabel.negative
            negative = min(0.9, 0.55 + negative_hits * 0.12)
            positive = max(0.05, 0.25 - negative_hits * 0.04)
        elif positive_hits and negative_hits:
            label = SentimentLabel.mixed
            positive = negative = 0.42
        else:
            label = SentimentLabel.neutral
            positive = negative = 0.18
        neutral = max(0.05, round(1.0 - positive - negative, 3))
        return SentimentResult(
            item_id=item.id,
            label=label,
            scores=SentimentScores(
                positive=round(positive, 3),
                neutral=round(neutral, 3),
                negative=round(negative, 3),
            ),
            key_phrases=extract_key_phrases(item.text, entity),
        )
