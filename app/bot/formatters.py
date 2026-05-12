from __future__ import annotations

from typing import Any

from app.config import settings
from app.database.models import Bet
from app.database.session import engine
from app.services.cache_service import default_cache
from app.services.football_response_service import FootballResponseService


def format_start_message() -> str:
    return (
        "Bem-vindo ao Analisador Inteligente de Futebol.\n\n"
        "Escolha Futebol para selecionar um jogo e receber uma leitura com IA: roteiro provavel, matchups, riscos e ideias qualitativas de mercados."
    )


def format_help_message() -> str:
    return (
        "Use o teclado para navegar.\n\n"
        "Fluxo recomendado: Futebol > Jogos de Hoje > Liga > Jogo. "
        "A analise mostra ideia geral, como o jogo deve ocorrer, pontos-chave, riscos, ideias de apostas e confianca.\n\n"
        "Comandos uteis: /start, /tutorial e /status."
    )


def format_status_message() -> str:
    api_key_status = "configurada" if settings.api_football_key else "ausente"
    api_mode = "RapidAPI" if "rapidapi.com" in settings.api_football_base_url else "API-Sports direto"
    db_mode = "SQLite" if settings.database_url.startswith("sqlite") else "PostgreSQL/externo"
    api_data_mode = "real" if settings.api_football_key else "mock/parcial"
    openai_mode = "ativo" if settings.openai_api_key else "fallback local"
    cache = default_cache.stats()
    return (
        "Status operacional\n\n"
        f"Ambiente: {settings.environment}\n"
        f"Banco: {db_mode} ({engine.url.drivername})\n"
        f"Cache: {cache['entries']} entradas | hits {cache['hits']} | misses {cache['misses']}\n\n"
        f"API-Football key: {api_key_status}\n"
        f"Modo API-Football: {api_mode}\n"
        f"Dados de futebol: {api_data_mode}\n"
        f"Base URL: {settings.api_football_base_url}\n\n"
        f"OpenAI/LLM: {openai_mode}\n"
        "Produto ativo: analisador de jogos de futebol com IA\n"
        "Modulos ativos: roteiro do jogo, contexto competitivo, escalações/desfalques quando disponiveis, jogadores e qualidade dos dados.\n\n"
        "Limitacoes: com dados parciais, a confianca cai; ideias de mercado nao sao garantia de resultado."
    )


def format_bet_advisor_response(advice: dict[str, Any]) -> str:
    return FootballResponseService().format_advice(advice)


def format_pre_match_card(card: dict[str, Any]) -> str:
    advice = card.get("advice") if isinstance(card, dict) else None
    if advice:
        return format_bet_advisor_response(advice)
    return str(card)


# Legacy helpers kept for old imports/tests. They are not exposed in the active bot UI.
def format_value_response(value: dict[str, Any]) -> str:
    return "Modulo de precificacao removido da experiencia ativa. Use a analise do jogo para leitura qualitativa."


def format_player_advice(player_advice: dict[str, Any]) -> str:
    player = player_advice.get("player") or "Jogador"
    lines = [
        "Leitura de jogador",
        "",
        f"{player}: {player_advice.get('selection') or player_advice.get('main_market') or 'dados insuficientes'}",
        "",
        "Por que faz sentido:",
    ]
    lines.extend(_bullet_lines(player_advice.get("key_factors"), fallback="dados insuficientes para cravar uma ideia individual"))
    lines.extend(["", "O que pode atrapalhar:"])
    lines.extend(_bullet_lines(player_advice.get("warnings"), fallback="minutos, titularidade e matchup precisam ser confirmados"))
    lines.extend(["", f"Veredito: {player_advice.get('final_verdict') or 'Use como shortlist qualitativa.'}"])
    return "\n".join(lines)


def format_top_props_advice(props: dict[str, Any]) -> str:
    best = props.get("best")
    if not best:
        return "Ideias individuais\n\nNao vejo uma ideia clara aqui. Melhor nao forcar."
    return "\n".join(
        [
            "Ideias individuais",
            "",
            f"Melhor nome para {props.get('market')}: {best.get('player')}",
            f"Selecao: {best.get('market')}",
            f"Motivo: {best.get('reason') or 'melhor equilibrio entre media, tendencia e risco no ranking.'}",
        ]
    )


def format_bets_message(bets: list[Bet]) -> str:
    return "Modulo de acompanhamento removido da experiencia ativa."


def format_betting_dashboard(open_bets: list[Bet], settled_bets: list[Bet], roi_data: dict[str, Any]) -> str:
    return "Modulo de acompanhamento removido da experiencia ativa."


def format_roi_message(roi_data: dict[str, Any]) -> str:
    return "Modulo de acompanhamento removido da experiencia ativa."


def _bullet_lines(items: Any, fallback: str, limit: int = 5) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    if isinstance(items, str):
        return [f"- {items}"]
    return [f"- {item}" for item in list(items)[:limit]]
