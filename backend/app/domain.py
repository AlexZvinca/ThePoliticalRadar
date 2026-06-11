from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator


MAX_ANALYSIS_DAYS = 365 * 3 + 1


class SourceName(StrEnum):
    news = "news"
    youtube = "youtube"
    csv = "csv"


class SentimentLabel(StrEnum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    mixed = "mixed"


class AnalysisStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AnalysisRequest(BaseModel):
    entity: str = Field(min_length=2, max_length=120)
    country: str = Field(min_length=2, max_length=80)
    start_date: date
    end_date: date
    sources: list[SourceName] = Field(default_factory=lambda: [SourceName.csv])
    language: str = Field(default="auto", min_length=2, max_length=8)
    limit_per_source: int = Field(default=250, ge=5, le=1000)

    @model_validator(mode="after")
    def validate_date_window(self) -> "AnalysisRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        if (self.end_date - self.start_date).days > MAX_ANALYSIS_DAYS:
            raise ValueError("date range cannot exceed three years")
        return self


class SourceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: SourceName
    text: str
    published_at: datetime
    title: str | None = None
    author: str | None = None
    url: HttpUrl | str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class SentimentScores(BaseModel):
    positive: float
    neutral: float
    negative: float


class SentimentResult(BaseModel):
    item_id: str
    label: SentimentLabel
    scores: SentimentScores
    key_phrases: list[str] = Field(default_factory=list)


class EventAnnotation(BaseModel):
    date: date
    title: str
    source: str = "news"
    url: HttpUrl | str | None = None
    tone: float | None = None


class EntityProfile(BaseModel):
    title: str
    description: str | None = None
    extract: str | None = None
    image_url: HttpUrl | str | None = None
    page_url: HttpUrl | str | None = None
    source: str = "wikipedia"


class DailySentimentPoint(BaseModel):
    date: date
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    mixed: int = 0
    average_score: float = 0.0
    volume: int = 0


class Peak(BaseModel):
    date: date
    volume: int
    negative_share: float
    note: str


class AggregateSnapshot(BaseModel):
    total_items: int
    sentiment_distribution: dict[SentimentLabel, int]
    source_distribution: dict[SourceName, int]
    daily: list[DailySentimentPoint]
    peaks: list[Peak]
    key_phrases: list[tuple[str, int]]
    representatives: dict[SentimentLabel, list[SourceItem]]
    events: list[EventAnnotation]


class Analysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: AnalysisRequest
    status: AnalysisStatus = AnalysisStatus.queued
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    profile: EntityProfile | None = None
    items: list[SourceItem] = Field(default_factory=list)
    sentiments: list[SentimentResult] = Field(default_factory=list)
    aggregates: AggregateSnapshot | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
