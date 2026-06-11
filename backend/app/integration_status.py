from __future__ import annotations

from pydantic import BaseModel


class AzureLanguageStatus(BaseModel):
    configured: bool
    ok: bool
    mode: str
    message: str


class IntegrationStatus(BaseModel):
    azure_language: AzureLanguageStatus
    youtube_configured: bool
    database_configured: bool
