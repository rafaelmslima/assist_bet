from __future__ import annotations

from enum import StrEnum

from app.bot.keyboards import (
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


class UserIntent(StrEnum):
    FOOTBALL = "football"
    BEST_GAMES = "best_games"
    PLAYERS_OF_DAY = "players_of_day"
    BACK = "back"
    ANALYZE_GAME = "analyze_game"
    ANALYZE_TEAM = "analyze_team"
    ANALYZE_PLAYER = "analyze_player"
    TOP_PROPS = "top_props"
    TODAY_GAMES = "today_games"
    TOMORROW_GAMES = "tomorrow_games"
    PRE_GAME_CARD = "pre_game_card"
    HELP = "help"
    SETTINGS = "settings"

    # Legacy intents kept for safe imports; they are not exposed by the active UI.
    NBA = "nba"
    NBA_TODAY_GAMES = "nba_today_games"
    NBA_TOMORROW_GAMES = "nba_tomorrow_games"
    NBA_PLAYERS_OF_DAY = "nba_players_of_day"
    NBA_BEST_GAMES = "nba_best_games"
    VIEW_ODDS = "view_odds"
    VALUE_BETTING = "value_betting"
    REGISTER_BET = "register_bet"
    MY_BETS = "my_bets"


BUTTON_TO_INTENT = {
    BTN_FOOTBALL: UserIntent.FOOTBALL,
    BTN_BEST_GAMES: UserIntent.BEST_GAMES,
    BTN_SEARCH_PLAYER: UserIntent.PLAYERS_OF_DAY,
    BTN_SEARCH_GAME: UserIntent.ANALYZE_GAME,
    BTN_BACK: UserIntent.BACK,
    BTN_TODAY: UserIntent.TODAY_GAMES,
    BTN_TOMORROW: UserIntent.TOMORROW_GAMES,
    BTN_HELP: UserIntent.HELP,
    BTN_SETTINGS: UserIntent.SETTINGS,
}


INTENT_PROMPTS = {
    UserIntent.ANALYZE_GAME: "Digite o jogo no formato: Arsenal x Chelsea",
    UserIntent.ANALYZE_TEAM: "A analise isolada de time foi removida. Envie um confronto: Time A x Time B.",
    UserIntent.ANALYZE_PLAYER: "Escolha um jogo em Futebol > Jogadores do Jogo para considerar contexto, escalação e matchup.",
    UserIntent.TOP_PROPS: "Escolha um jogo em Futebol > Jogadores do Jogo para gerar ideias individuais com dados reais.",
    UserIntent.PRE_GAME_CARD: "Digite o jogo no formato: Arsenal x Chelsea",
}
