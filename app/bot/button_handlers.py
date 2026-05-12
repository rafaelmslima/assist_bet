from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.fixture_callbacks import show_leagues_menu, show_player_leagues_menu, show_tomorrow_leagues_menu
from app.bot.intents import BUTTON_TO_INTENT, INTENT_PROMPTS, UserIntent
from app.bot.keyboards import football_menu_keyboard, main_menu_keyboard
from app.bot.state import clear_user_state, set_user_intent
from app.bot.tutorial import start_tutorial
from app.services.fixture_menu_service import FixtureMenuService


async def button_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle fixed keyboard button clicks."""
    if update.effective_user is None or update.effective_chat is None or update.message is None or update.message.text is None:
        return

    intent = BUTTON_TO_INTENT.get(update.message.text)
    if intent is None:
        return

    telegram_user_id = update.effective_user.id

    if intent == UserIntent.FOOTBALL:
        clear_user_state(telegram_user_id)
        context.user_data["sport_menu"] = "football"
        await update.message.reply_text(
            "Futebol: escolha um jogo para gerar uma leitura inteligente com IA.",
            reply_markup=football_menu_keyboard(),
        )
        return

    if intent == UserIntent.BACK:
        clear_user_state(telegram_user_id)
        context.user_data["sport_menu"] = None
        await update.message.reply_text("Menu principal.", reply_markup=main_menu_keyboard())
        return

    if intent == UserIntent.HELP:
        clear_user_state(telegram_user_id)
        await start_tutorial(update, context)
        return

    if intent == UserIntent.SETTINGS:
        clear_user_state(telegram_user_id)
        from app.bot.formatters import format_status_message

        await update.message.reply_text(format_status_message(), reply_markup=main_menu_keyboard())
        return

    if intent == UserIntent.TODAY_GAMES:
        clear_user_state(telegram_user_id)
        await show_leagues_menu(update, context)
        return

    if intent == UserIntent.TOMORROW_GAMES:
        clear_user_state(telegram_user_id)
        await show_tomorrow_leagues_menu(update, context)
        return

    if intent == UserIntent.BEST_GAMES:
        clear_user_state(telegram_user_id)
        await update.message.reply_text(
            FixtureMenuService().get_best_games_today(),
            reply_markup=football_menu_keyboard(),
        )
        return

    if intent == UserIntent.PLAYERS_OF_DAY:
        clear_user_state(telegram_user_id)
        await show_player_leagues_menu(update, context)
        return

    set_user_intent(telegram_user_id, intent)
    await update.message.reply_text(
        INTENT_PROMPTS[intent],
        reply_markup=football_menu_keyboard() if intent == UserIntent.ANALYZE_GAME else main_menu_keyboard(),
    )
