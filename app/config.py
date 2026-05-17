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


def _web_secret_key_from_env() -> str:
    default = "dev-insecure-change-me-please-32-bytes"
    value = os.getenv("WEB_SECRET_KEY", default)
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    if is_production and (value == default or len(value) < 32):
        raise RuntimeError("WEB_SECRET_KEY forte e obrigatoria quando ENVIRONMENT=production.")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = _database_url_from_env()

    api_football_key: str | None = os.getenv("API_FOOTBALL_KEY")
    api_football_base_url: str = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
    api_football_host: str | None = os.getenv("API_FOOTBALL_HOST")

    environment: str = os.getenv("ENVIRONMENT", "development")
    database_create_all: bool = _truthy_env("DATABASE_CREATE_ALL")
    database_migrate_on_startup: bool = _migrate_on_startup_from_env()
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    web_secret_key: str = _web_secret_key_from_env()
    web_session_cookie_name: str = os.getenv("WEB_SESSION_COOKIE_NAME", "assist_bet_session")
    web_session_expire_minutes: int = int(os.getenv("WEB_SESSION_EXPIRE_MINUTES", "10080"))
    login_rate_limit_attempts: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    login_rate_limit_window_seconds: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
    fixture_payload_cache_seconds: int = int(os.getenv("FIXTURE_PAYLOAD_CACHE_SECONDS", "300"))
    password_reset_code: str | None = os.getenv("PASSWORD_RESET_CODE")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
