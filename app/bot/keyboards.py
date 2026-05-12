from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


BTN_FOOTBALL = "Futebol"
BTN_SETTINGS = "Status"
BTN_HELP = "Ajuda"
BTN_TODAY = "Jogos de Hoje"
BTN_TOMORROW = "Jogos de Amanha"
BTN_SEARCH_GAME = "Buscar Jogo"
BTN_SEARCH_PLAYER = "Jogadores do Jogo"
BTN_BEST_GAMES = "Melhores Leituras"
BTN_AVOID = "Jogos para Evitar"
BTN_BACK = "Voltar"

# Legacy constants kept so old modules can import safely while the active UI stays football-only.
BTN_NBA = "NBA"
BTN_MY_BETS = "Minhas Apostas"
BTN_NBA_BEST = "Melhores Props"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the fixed main reply keyboard."""
    keyboard = [
        [KeyboardButton(BTN_FOOTBALL)],
        [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_HELP)],
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
    """Legacy compatibility keyboard; NBA is no longer exposed in the active menu."""
    return main_menu_keyboard()
