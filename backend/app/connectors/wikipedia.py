from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from app.config import Settings
from app.domain import AnalysisRequest, EntityProfile


async def fetch_wikipedia_profile(request: AnalysisRequest, settings: Settings) -> EntityProfile | None:
    search_queries = _search_queries(request)
    languages = _candidate_languages(request.language)
    user_agent = settings.wikimedia_user_agent or settings.http_user_agent
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
        last_error: Exception | None = None
        candidates: list[tuple[int, EntityProfile]] = []
        for language in languages:
            for search_query in search_queries:
                try:
                    candidates.extend(await _fetch_from_language(client, language, search_query, request))
                except httpx.HTTPError as exc:
                    last_error = exc
        if candidates:
            score, profile = max(candidates, key=lambda candidate: candidate[0])
            if score >= 2:
                return profile
        if last_error:
            raise last_error
    return None


async def _fetch_from_language(
    client: httpx.AsyncClient,
    language: str,
    search_query: str,
    request: AnalysisRequest,
) -> list[tuple[int, EntityProfile]]:
    search_response = await client.get(
        f"https://{language}.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": search_query,
            "format": "json",
            "srlimit": 5,
            "origin": "*",
        },
    )
    search_response.raise_for_status()
    results = search_response.json().get("query", {}).get("search", [])
    if not results:
        return []

    candidates: list[tuple[int, EntityProfile]] = []
    for result in results:
        title = result["title"]
        summary_response = await client.get(
            f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}",
        )
        if summary_response.status_code == 404:
            continue
        summary_response.raise_for_status()
        summary = summary_response.json()
        score = _profile_score(summary, request)
        candidates.append((score, _profile_from_summary(summary, title)))
    return candidates


def _profile_from_summary(summary: dict, fallback_title: str) -> EntityProfile:
    title = summary.get("title") or fallback_title
    thumbnail = summary.get("thumbnail") or {}
    content_urls = summary.get("content_urls") or {}
    desktop_url = (content_urls.get("desktop") or {}).get("page")
    return EntityProfile(
        title=title,
        description=summary.get("description"),
        extract=summary.get("extract"),
        image_url=thumbnail.get("source"),
        page_url=desktop_url,
    )


def _search_queries(request: AnalysisRequest) -> list[str]:
    entity = request.entity.strip()
    country = request.country.strip()
    return [
        f'intitle:"{entity}" {country} politician OR party OR politics',
        f'"{entity}" {country} politician OR party OR politics',
        f"{entity} {country}",
    ]


def _profile_score(summary: dict, request: AnalysisRequest) -> int:
    entity_tokens = _tokens(request.entity)
    country_tokens = _tokens(request.country)
    title = summary.get("title") or ""
    description = summary.get("description") or ""
    extract = summary.get("extract") or ""
    haystack = f"{title} {description} {extract}".casefold()
    title_tokens = _tokens(title)
    score = 0
    score += 4 * len(entity_tokens & title_tokens)
    score += 2 * len(entity_tokens & _tokens(haystack))
    score += len(country_tokens & _tokens(haystack))
    political_terms = {
        "politician",
        "political",
        "party",
        "parliament",
        "minister",
        "senator",
        "deputy",
        "president",
        "romania",
        "romanian",
        "politician român",
        "partid",
        "politic",
    }
    if any(term in haystack for term in political_terms):
        score += 3
    return score


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\w]+", value) if len(token) > 1}


def _candidate_languages(language: str) -> list[str]:
    supported = {"ro", "en", "fr", "de", "it", "es", "pl", "hu", "uk"}
    first = language.lower() if language.lower() in supported else "en"
    languages = [first]
    if first != "en":
        languages.append("en")
    return languages
