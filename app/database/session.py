from __future__ import annotations

from collections.abc import Generator
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import Base


logger = logging.getLogger(__name__)


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(settings.database_url, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create local development tables when migrations are not managing startup."""
    if settings.environment.lower() == "production" and not settings.database_create_all:
        logger.info("Skipping create_all in production; run Alembic migrations before startup.")
        return
    Base.metadata.create_all(bind=engine)


def run_migrations() -> None:
    """Apply Alembic migrations before the web app starts."""
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(f"Alembic config not found at {alembic_ini}")

    logger.info("Running database migrations with Alembic")
    config = Config(str(alembic_ini))
    command.upgrade(config, "head")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
