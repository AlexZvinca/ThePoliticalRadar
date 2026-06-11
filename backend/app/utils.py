from __future__ import annotations

import re
from collections.abc import Iterable

from app.domain import SourceItem

URL_RE = re.compile(r"https?://\S+")
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
MAX_RETAINED_TEXT_CHARS = 600

STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "being",
    "could",
    "from",
    "have",
    "into",
    "more",
    "only",
    "over",
    "people",
    "political",
    "politician",
    "party",
    "said",
    "should",
    "their",
    "there",
    "these",
    "they",
    "this",
    "that",
    "with",
    "would",
}


def clean_text(text: str) -> str:
    without_urls = URL_RE.sub("", text)
    compact = SPACE_RE.sub(" ", without_urls).strip()
    if len(compact) <= MAX_RETAINED_TEXT_CHARS:
        return compact
    return f"{compact[: MAX_RETAINED_TEXT_CHARS - 3].rstrip()}..."


def deduplicate_items(items: Iterable[SourceItem]) -> list[SourceItem]:
    seen: set[str] = set()
    result: list[SourceItem] = []
    for item in items:
        item.text = clean_text(item.text)
        key = item.text.casefold()
        if len(item.text) < 8 or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def extract_key_phrases(text: str, entity: str) -> list[str]:
    words = [word.casefold().strip("'") for word in WORD_RE.findall(text)]
    entity_words = {part.casefold() for part in WORD_RE.findall(entity)}
    phrases: list[str] = []
    for word in words:
        if word in STOP_WORDS or word in entity_words:
            continue
        if word not in phrases:
            phrases.append(word)
        if len(phrases) == 6:
            break
    return phrases
