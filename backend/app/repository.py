from __future__ import annotations

from threading import Lock

from app.domain import Analysis


class AnalysisRepository:
    """Small in-memory repository for MVP/demo runs.

    The data model is PostgreSQL-ready; `database/schema.sql` contains the Azure
    Database for PostgreSQL deployment schema.
    """

    def __init__(self) -> None:
        self._analyses: dict[str, Analysis] = {}
        self._lock = Lock()

    def save(self, analysis: Analysis) -> Analysis:
        with self._lock:
            self._analyses[analysis.id] = analysis
            return analysis

    def get(self, analysis_id: str) -> Analysis | None:
        with self._lock:
            return self._analyses.get(analysis_id)

    def list(self) -> list[Analysis]:
        with self._lock:
            return sorted(self._analyses.values(), key=lambda item: item.created_at, reverse=True)


repository = AnalysisRepository()

