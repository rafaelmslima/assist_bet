from __future__ import annotations

from enum import StrEnum


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
    "⚽ Futebol": UserIntent.FOOTBALL,
    "🏀 NBA": UserIntent.NBA,
    "⭐ Jogos com Melhor Leitura": UserIntent.BEST_GAMES,
    "👟 Jogadores do Dia": UserIntent.PLAYERS_OF_DAY,
    "🔎 Buscar Jogo": UserIntent.ANALYZE_GAME,
    "⬅️ Voltar": UserIntent.BACK,
    "📅 Jogos de Hoje": UserIntent.TODAY_GAMES,
    "📆 Jogos de Amanhã": UserIntent.TOMORROW_GAMES,
    "📈 Minhas Apostas": UserIntent.MY_BETS,
    "❓ Ajuda": UserIntent.HELP,
    "⚙️ Configurações": UserIntent.SETTINGS,
    "🏀 Jogos de Hoje": UserIntent.NBA_TODAY_GAMES,
    "🏀 Jogos de Amanhã": UserIntent.NBA_TOMORROW_GAMES,
    "🏀 Jogadores do Dia": UserIntent.NBA_PLAYERS_OF_DAY,
    "🏀 Jogos com Melhor Leitura": UserIntent.NBA_BEST_GAMES,
    "⚽ Futebol": UserIntent.FOOTBALL,
    "🏀 NBA": UserIntent.NBA,
    "⭐ Jogos com Melhor Leitura": UserIntent.BEST_GAMES,
    "👟 Jogadores do Dia": UserIntent.PLAYERS_OF_DAY,
    "🔎 Buscar Jogo": UserIntent.ANALYZE_GAME,
    "⬅️ Voltar": UserIntent.BACK,
    "📊 Analisar Jogo": UserIntent.ANALYZE_GAME,
    "🏟️ Analisar Time": UserIntent.ANALYZE_TEAM,
    "👤 Analisar Jogador": UserIntent.ANALYZE_PLAYER,
    "🔥 Top Props": UserIntent.TOP_PROPS,
    "📅 Jogos de Hoje": UserIntent.TODAY_GAMES,
    "💰 Ver Odds": UserIntent.VIEW_ODDS,
    "🧠 Value Betting": UserIntent.VALUE_BETTING,
    "🧾 Card Pré-Jogo": UserIntent.PRE_GAME_CARD,
    "➕ Registrar Aposta": UserIntent.REGISTER_BET,
    "📈 Minhas Apostas": UserIntent.MY_BETS,
    "❓ Ajuda": UserIntent.HELP,
    "⚙️ Configurações": UserIntent.SETTINGS,
}


INTENT_PROMPTS = {
    UserIntent.ANALYZE_GAME: "Digite o jogo no formato: Arsenal x Chelsea",
    UserIntent.ANALYZE_TEAM: "Digite o nome do time:",
    UserIntent.ANALYZE_PLAYER: "Digite o nome do jogador:",
    UserIntent.TOP_PROPS: "Digite o time e o mercado. Ex: Arsenal finalizações",
    UserIntent.VIEW_ODDS: "Digite o jogo:",
    UserIntent.VALUE_BETTING: "Digite o jogo e a odd. Ex: Arsenal x Chelsea odd 1.80",
    UserIntent.PRE_GAME_CARD: "Digite o jogo:",
    UserIntent.REGISTER_BET: (
        "Envie no formato:\n"
        "jogo | mercado | seleção | odd | stake | motivo\n\n"
        "Ex: Arsenal x Chelsea | finalizações | Saka over 2.5 | 1.85 | 50 | Chelsea cede muitas finalizações pelo lado esquerdo"
    ),
}
