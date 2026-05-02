from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.formatters import format_betting_dashboard, format_roi_message
from app.bot.keyboards import main_menu_keyboard
from app.database.repository import get_or_create_user
from app.database.session import SessionLocal
from app.services.betting_service import BettingService


async def bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None or update.message is None:
        return

    message = _build_betting_dashboard_message(update)
    await update.message.reply_text(message, reply_markup=main_menu_keyboard())


async def roi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None or update.message is None:
        return

    with SessionLocal() as db:
        user = get_or_create_user(
            db,
            telegram_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )
        roi_data = BettingService(db).calculate_user_roi(user_id=user.id)

    await update.message.reply_text(format_roi_message(roi_data), reply_markup=main_menu_keyboard())


async def result_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None or update.message is None:
        return

    args = context.args or []
    if len(args) != 2:
        await update.message.reply_text(
            "Use: /resultado ID status\n"
            "Status possíveis: won, lost, void\n"
            "Ex: /resultado 12 won",
            reply_markup=main_menu_keyboard(),
        )
        return

    try:
        bet_id = int(args[0])
    except ValueError:
        await update.message.reply_text("O ID da aposta precisa ser um número.", reply_markup=main_menu_keyboard())
        return

    status = args[1].lower()
    if status not in {"won", "lost", "void"}:
        await update.message.reply_text("Status possíveis: won, lost, void.", reply_markup=main_menu_keyboard())
        return

    with SessionLocal() as db:
        user = get_or_create_user(
            db,
            telegram_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )
        bet = BettingService(db).settle_bet(bet_id=bet_id, user_id=user.id, status=status)

    if bet is None:
        await update.message.reply_text("Aposta não encontrada para seu usuário.", reply_markup=main_menu_keyboard())
        return

    await update.message.reply_text(
        f"Aposta #{bet.id} atualizada para {bet.status}. Lucro/prejuízo: {bet.profit_loss:.2f}",
        reply_markup=main_menu_keyboard(),
    )


def _build_betting_dashboard_message(update: Update) -> str:
    with SessionLocal() as db:
        user = get_or_create_user(
            db,
            telegram_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )
        service = BettingService(db)
        open_bets = service.list_open_bets(user_id=user.id)
        settled_bets = service.list_recent_settled_bets(user_id=user.id)
        roi_data = service.calculate_user_roi(user_id=user.id)

    return format_betting_dashboard(open_bets, settled_bets, roi_data)


def build_betting_dashboard_message(update: Update) -> str:
    return _build_betting_dashboard_message(update)
