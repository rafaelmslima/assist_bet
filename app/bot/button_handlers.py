from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.betting_handlers import build_betting_dashboard_message
from app.bot.fixture_callbacks import show_leagues_menu, show_player_leagues_menu, show_tomorrow_leagues_menu
from app.bot.intents import BUTTON_TO_INTENT, INTENT_PROMPTS, UserIntent
from app.bot.keyboards import football_menu_keyboard, main_menu_keyboard, nba_menu_keyboard
from app.bot.nba_callbacks import show_nba_games_menu, show_nba_players_menu, show_nba_tomorrow_games_menu
from app.bot.state import clear_user_state, set_user_intent
from app.bot.tutorial import start_tutorial
from app.services.fixture_menu_service import FixtureMenuService
from app.services.nba_game_menu_service import NbaGameMenuService


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
        await update.message.reply_text(
            "Futebol: escolha como você quer encontrar a melhor leitura.",
            reply_markup=football_menu_keyboard(),
        )
        return

    if intent == UserIntent.NBA:
        clear_user_state(telegram_user_id)
        await update.message.reply_text(
            "NBA: escolha um jogo para eu buscar props de jogadores com leitura por posição, minutos e matchup.",
            reply_markup=nba_menu_keyboard(),
        )
        return

    if intent == UserIntent.NBA_TODAY_GAMES:
        clear_user_state(telegram_user_id)
        await show_nba_games_menu(update, context)
        return

    if intent == UserIntent.NBA_TOMORROW_GAMES:
        clear_user_state(telegram_user_id)
        await show_nba_tomorrow_games_menu(update, context)
        return

    if intent == UserIntent.NBA_PLAYERS_OF_DAY:
        clear_user_state(telegram_user_id)
        await show_nba_players_menu(update, context)
        return

    if intent == UserIntent.NBA_BEST_GAMES:
        clear_user_state(telegram_user_id)
        await update.message.reply_text(
            NbaGameMenuService().get_best_games_today(),
            reply_markup=nba_menu_keyboard(),
        )
        return

    if intent == UserIntent.BACK:
        clear_user_state(telegram_user_id)
        await update.message.reply_text("Menu principal.", reply_markup=main_menu_keyboard())
        return

    if intent == UserIntent.HELP:
        clear_user_state(telegram_user_id)
        await start_tutorial(update, context)
        return

    if intent == UserIntent.SETTINGS:
        clear_user_state(telegram_user_id)
        await update.message.reply_text(
            "Configurações ainda serão implementadas. Por enquanto, use o teclado para iniciar uma análise.",
            reply_markup=main_menu_keyboard(),
        )
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

    if intent == UserIntent.MY_BETS:
        clear_user_state(telegram_user_id)
        await update.message.reply_text(
            build_betting_dashboard_message(update),
            reply_markup=main_menu_keyboard(),
        )
        return

    set_user_intent(telegram_user_id, intent)
    await update.message.reply_text(
        INTENT_PROMPTS[intent],
        reply_markup=football_menu_keyboard() if intent == UserIntent.ANALYZE_GAME else main_menu_keyboard(),
    )
