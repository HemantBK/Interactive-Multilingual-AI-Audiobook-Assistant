"""
Central configuration via Pydantic Settings.
Loads from environment variables (and the repo-root `.env` locally).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → parents: [core, app, backend, <repo root>]
REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    gemini_api_key: str = ""
    groq_api_key: str = ""

    rate_limit_per_ip_per_min: int = 10
    rate_limit_daily_uploads: int = 10
    rate_limit_daily_queries: int = 500
    rate_limit_daily_tts_chars: int = 100_000

    max_upload_mb: int = 50

    kill_switch: bool = False

    sentry_dsn_backend: str = ""
    posthog_api_key_backend: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
