from __future__ import annotations

from enum import StrEnum

from app.bot.keyboards import (
    BTN_BACK,
    BTN_BEST_GAMES,
    BTN_FOOTBALL,
    BTN_HELP,
    BTN_MY_BETS,
    BTN_NBA,
    BTN_NBA_BEST,
    BTN_SEARCH_GAME,
    BTN_SEARCH_PLAYER,
    BTN_SETTINGS,
    BTN_TODAY,
    BTN_TOMORROW,
)


class UserIntent(StrEnum):
    FOOTBALL = "football"
    NBA = "nba"
    NBA_TODAY_GAMES = "nba_today_games"
    NBA_TOMORROW_GAMES = "nba_tomorrow_games"
    NBA_PLAYERS_OF_DAY = "nba_players_of_day"
    NBA_BEST_GAMES = "nba_best_games"
    BEST_GAMES = "best_games"
    PLAYERS_OF_DAY = "players_of_day"
    BACK = "back"
    ANALYZE_GAME = "analyze_game"
    ANALYZE_TEAM = "analyze_team"
    ANALYZE_PLAYER = "analyze_player"
    TOP_PROPS = "top_props"
    TODAY_GAMES = "today_games"
    TOMORROW_GAMES = "tomorrow_games"
    VIEW_ODDS = "view_odds"
    VALUE_BETTING = "value_betting"
    PRE_GAME_CARD = "pre_game_card"
    REGISTER_BET = "register_bet"
    MY_BETS = "my_bets"
    HELP = "help"
    SETTINGS = "settings"


BUTTON_TO_INTENT = {
    BTN_FOOTBALL: UserIntent.FOOTBALL,
    BTN_NBA: UserIntent.NBA,
    BTN_BEST_GAMES: UserIntent.BEST_GAMES,
    BTN_SEARCH_PLAYER: UserIntent.PLAYERS_OF_DAY,
    BTN_SEARCH_GAME: UserIntent.ANALYZE_GAME,
    BTN_BACK: UserIntent.BACK,
    BTN_TODAY: UserIntent.TODAY_GAMES,
    BTN_TOMORROW: UserIntent.TOMORROW_GAMES,
    BTN_MY_BETS: UserIntent.MY_BETS,
    BTN_HELP: UserIntent.HELP,
    BTN_SETTINGS: UserIntent.SETTINGS,
    BTN_NBA_BEST: UserIntent.NBA_BEST_GAMES,
}


INTENT_PROMPTS = {
    UserIntent.ANALYZE_GAME: "Digite o jogo no formato: Arsenal x Chelsea",
    UserIntent.ANALYZE_TEAM: "Digite o nome do time:",
    UserIntent.ANALYZE_PLAYER: "Digite o nome do jogador:",
    UserIntent.TOP_PROPS: "Digite o time e o mercado. Ex: Arsenal finalizacoes",
    UserIntent.VIEW_ODDS: "Digite o jogo:",
    UserIntent.VALUE_BETTING: "Digite o jogo e a odd. Ex: Arsenal x Chelsea odd 1.80",
    UserIntent.PRE_GAME_CARD: "Digite o jogo:",
    UserIntent.REGISTER_BET: (
        "Envie no formato:\n"
        "jogo | mercado | selecao | odd | stake | motivo\n\n"
        "Ex: Arsenal x Chelsea | finalizacoes | Saka over 2.5 | 1.85 | 50 | Chelsea cede muitas finalizacoes pelo lado esquerdo"
    ),
}
