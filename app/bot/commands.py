from __future__ import annotations

import re

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.button_handlers import button_message_handler
from app.bot.command_handlers import help_command, start_command, status_command
from app.bot.error_handlers import telegram_error_handler
from app.bot.fixture_callbacks import fixture_callback_handler
from app.bot.keyboards import (
    BTN_AVOID,
    BTN_BACK,
    BTN_BEST_GAMES,
    BTN_FOOTBALL,
    BTN_HELP,
    BTN_SEARCH_GAME,
    BTN_SEARCH_PLAYER,
    BTN_SETTINGS,
    BTN_TODAY,
    BTN_TOMORROW,
)
from app.bot.text_handlers import free_text_handler
from app.bot.tutorial import start_tutorial, tutorial_step_handler


BUTTON_TEXTS = (
    BTN_FOOTBALL,
    BTN_SETTINGS,
    BTN_HELP,
    BTN_TODAY,
    BTN_TOMORROW,
    BTN_SEARCH_GAME,
    BTN_SEARCH_PLAYER,
    BTN_BEST_GAMES,
    BTN_AVOID,
    BTN_BACK,
)


def register_commands(application: Application) -> None:
    """Register Telegram command handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tutorial", start_tutorial))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(tutorial_step_handler, pattern=r"^tutorial_"))
    application.add_handler(
        CallbackQueryHandler(
            fixture_callback_handler,
            pattern=r"^(fixtures_|players_|fixture_)",
        )
    )
    button_pattern = "^(" + "|".join(re.escape(text) for text in BUTTON_TEXTS) + ")$"
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(button_pattern), button_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_handler))
    application.add_error_handler(telegram_error_handler)
