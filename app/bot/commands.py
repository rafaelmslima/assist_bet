from __future__ import annotations

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.betting_handlers import bets_command, result_command, roi_command
from app.bot.command_handlers import help_command, start_command, status_command
from app.bot.error_handlers import telegram_error_handler
from app.bot.handlers import button_router, fixture_callback
from app.bot.tutorial import start_tutorial, tutorial_step_handler


def register_commands(application: Application) -> None:
    """Register Telegram command handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tutorial", start_tutorial))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("apostas", bets_command))
    application.add_handler(CommandHandler("roi", roi_command))
    application.add_handler(CommandHandler("resultado", result_command))
    application.add_handler(CallbackQueryHandler(tutorial_step_handler, pattern=r"^tutorial_"))
    application.add_handler(CallbackQueryHandler(fixture_callback, pattern=r"^rec:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_router))
    application.add_error_handler(telegram_error_handler)
