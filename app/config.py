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


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
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
    database_create_all: bool = os.getenv("DATABASE_CREATE_ALL", "").lower() in {"1", "true", "yes"}
    bot_analysis_style: str = os.getenv("BOT_ANALYSIS_STYLE", "advisor")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


settings = Settings()
