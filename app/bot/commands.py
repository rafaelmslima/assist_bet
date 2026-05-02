from __future__ import annotations

import re

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.betting_handlers import bets_command, result_command, roi_command
from app.bot.button_handlers import button_message_handler
from app.bot.command_handlers import help_command, start_command, status_command
from app.bot.error_handlers import telegram_error_handler
from app.bot.fixture_callbacks import fixture_callback_handler
from app.bot.intents import BUTTON_TO_INTENT
from app.bot.nba_callbacks import nba_callback_handler
from app.bot.text_handlers import free_text_handler
from app.bot.tutorial import start_tutorial, tutorial_step_handler


def register_commands(application: Application) -> None:
    """Register Telegram command handlers."""
    button_pattern = f"^({'|'.join(re.escape(button) for button in BUTTON_TO_INTENT)})$"

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tutorial", start_tutorial))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("apostas", bets_command))
    application.add_handler(CommandHandler("roi", roi_command))
    application.add_handler(CommandHandler("resultado", result_command))
    application.add_handler(CallbackQueryHandler(tutorial_step_handler, pattern=r"^tutorial_"))
    application.add_handler(
        CallbackQueryHandler(
            fixture_callback_handler,
            pattern=r"^(fixtures_|players_|fixture_analyze_|fixture_card_|fixture_players_|fixture_injuries_)",
        )
    )
    application.add_handler(CallbackQueryHandler(nba_callback_handler, pattern=r"^nba_"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(button_pattern), button_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_handler))
    application.add_error_handler(telegram_error_handler)
