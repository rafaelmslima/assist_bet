from __future__ import annotations

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard


logger = logging.getLogger(__name__)


async def telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log bot errors safely and send a small recovery message when possible."""
    error = context.error
    if isinstance(error, BadRequest) and "message is not modified" in str(error).lower():
        return

    exc_info = (type(error), error, error.__traceback__) if error else None
    logger.error("Unhandled Telegram bot error: %s", error.__class__.__name__ if error else "unknown", exc_info=exc_info)

    if not isinstance(update, Update) or update.effective_chat is None:
        return

    await update.effective_chat.send_message(
        "Tive um problema ao processar essa acao. Voltei para o menu para voce tentar de novo.",
        reply_markup=main_menu_keyboard(),
    )
