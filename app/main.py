from __future__ import annotations

import logging
import sys
from pathlib import Path

from telegram.ext import Application

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bot.commands import register_commands
from app.config import settings
from app.database.session import init_db, run_migrations


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Build and configure the Telegram bot application."""
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Copy .env.example to .env and set the token."
        )

    application = Application.builder().token(settings.telegram_bot_token).build()
    register_commands(application)
    return application


def main() -> None:
    """Application entry point."""
    if settings.database_migrate_on_startup:
        run_migrations()
    init_db()
    application = create_application()

    logger.info("Starting Sports Betting Assistant bot")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
