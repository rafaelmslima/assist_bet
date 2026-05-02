from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_start_message, format_status_message
from app.bot.keyboards import main_menu_keyboard
from app.bot.tutorial import start_tutorial, start_tutorial_keyboard
from app.database.repository import get_or_create_user
from app.database.session import SessionLocal


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start."""
    if update.effective_user is None or update.effective_chat is None or update.message is None:
        return

    with SessionLocal() as db:
        get_or_create_user(
            db,
            telegram_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )

    await update.message.reply_text(
        format_start_message(),
        reply_markup=main_menu_keyboard(),
    )
    await update.message.reply_text(
        "Quer aprender a usar o bot?",
        reply_markup=start_tutorial_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    await start_tutorial(update, context)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status."""
    await update.message.reply_text(
        format_status_message(),
        reply_markup=main_menu_keyboard(),
    )
