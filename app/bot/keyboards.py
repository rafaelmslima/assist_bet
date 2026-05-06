from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


BTN_FOOTBALL = "⚽ Futebol"
BTN_NBA = "🏀 NBA"
BTN_MY_BETS = "📊 Minhas Apostas"
BTN_SETTINGS = "⚙️ Configurações"
BTN_HELP = "❓ Ajuda"
BTN_TODAY = "📅 Jogos de Hoje"
BTN_TOMORROW = "📆 Jogos de Amanhã"
BTN_SEARCH_GAME = "🔍 Buscar Jogo"
BTN_SEARCH_PLAYER = "👤 Buscar Jogador"
BTN_BEST_GAMES = "🔥 Melhores Leituras"
BTN_AVOID = "🚫 Jogos para Evitar"
BTN_BACK = "⬅️ Voltar"
BTN_NBA_BEST = "🔥 Melhores Props"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the fixed main reply keyboard."""
    keyboard = [
        [KeyboardButton(BTN_FOOTBALL), KeyboardButton(BTN_NBA)],
        [KeyboardButton(BTN_MY_BETS), KeyboardButton(BTN_SETTINGS)],
        [KeyboardButton(BTN_HELP)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha uma opcao",
    )


def football_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return football-focused navigation."""
    keyboard = [
        [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_TOMORROW)],
        [KeyboardButton(BTN_BEST_GAMES), KeyboardButton(BTN_SEARCH_GAME)],
        [KeyboardButton(BTN_SEARCH_PLAYER), KeyboardButton(BTN_AVOID)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha uma opcao de futebol",
    )


def nba_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return NBA-focused navigation."""
    keyboard = [
        [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_TOMORROW)],
        [KeyboardButton(BTN_NBA_BEST), KeyboardButton(BTN_SEARCH_GAME)],
        [KeyboardButton(BTN_SEARCH_PLAYER), KeyboardButton(BTN_AVOID)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha uma opcao de NBA",
    )
