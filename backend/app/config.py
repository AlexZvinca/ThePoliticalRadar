from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "The Political Radar"
    azure_language_endpoint: str | None = None
    azure_language_key: str | None = None
    youtube_api_key: str | None = None
    database_url: str | None = None
    request_timeout_seconds: float = 12.0
    http_user_agent: str = "ThePoliticalRadar/0.1 (academic cloud AI course project)"
    wikimedia_user_agent: str | None = None
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
