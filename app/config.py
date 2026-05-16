from __future__ import annotations

import os
from dataclasses import dataclass

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _database_url_from_env() -> str:
    raw_url = os.getenv("DATABASE_URL", "sqlite:///./sports_betting_assistant.db")
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes"}


def _migrate_on_startup_from_env() -> bool:
    raw_value = os.getenv("DATABASE_MIGRATE_ON_STARTUP")
    if raw_value is not None:
        return raw_value.lower() in {"1", "true", "yes"}
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


@dataclass(frozen=True)
class Settings:
    database_url: str = _database_url_from_env()

    api_football_key: str | None = os.getenv("API_FOOTBALL_KEY")
    api_football_base_url: str = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
    api_football_host: str | None = os.getenv("API_FOOTBALL_HOST")
    balldontlie_key: str | None = os.getenv("BALLDONTLIE_KEY")
    odds_api_key: str | None = os.getenv("ODDS_API_KEY")
    odds_api_regions: str = os.getenv("ODDS_API_REGIONS", "eu")
    odds_api_markets: str = os.getenv("ODDS_API_MARKETS", "h2h,totals")
    odds_api_odds_format: str = os.getenv("ODDS_API_ODDS_FORMAT", "decimal")

    environment: str = os.getenv("ENVIRONMENT", "development")
    database_create_all: bool = _truthy_env("DATABASE_CREATE_ALL")
    database_migrate_on_startup: bool = _migrate_on_startup_from_env()
    bot_analysis_style: str = os.getenv("BOT_ANALYSIS_STYLE", "advisor")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    web_secret_key: str = os.getenv("WEB_SECRET_KEY", "dev-insecure-change-me-please-32-bytes")
    web_session_cookie_name: str = os.getenv("WEB_SESSION_COOKIE_NAME", "assist_bet_session")
    web_session_expire_minutes: int = int(os.getenv("WEB_SESSION_EXPIRE_MINUTES", "10080"))

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
