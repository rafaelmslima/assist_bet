from __future__ import annotations

from typing import Any

from app.config import settings
from app.database.models import Bet
from app.database.session import engine
from app.services.cache_service import default_cache
from app.services.football_response_service import FootballResponseService


def format_start_message() -> str:
    return (
        "Bem-vindo ao Sports Betting Assistant.\n\n"
        "Escolha Futebol para encontrar jogos, comparar odds e receber uma leitura objetiva antes de apostar."
    )


def format_help_message() -> str:
    return (
        "Use o teclado para navegar.\n\n"
        "Fluxo recomendado: Futebol > Jogos de Hoje > Liga > Jogo. "
        "A analise mostra melhor aposta, risco, odd justa, value, contexto e o que confirmar antes da entrada.\n\n"
        "Comandos uteis: /apostas, /roi, /resultado ID won|lost|void e /status."
    )


def format_status_message() -> str:
    api_key_status = "configurada" if settings.api_football_key else "ausente"
    odds_key_status = "configurada" if settings.odds_api_key else "ausente"
    api_mode = "RapidAPI" if "rapidapi.com" in settings.api_football_base_url else "API-Sports direto"
    db_mode = "SQLite" if settings.database_url.startswith("sqlite") else "PostgreSQL/externo"
    api_data_mode = "real" if settings.api_football_key else "mock/parcial"
    odds_data_mode = "real" if settings.odds_api_key else "indisponivel"
    nba_mode = "real" if settings.balldontlie_key else "mock/parcial"
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
        f"Odds API key: {odds_key_status}\n"
        f"Dados de odds: {odds_data_mode}\n"
        f"Odds regions: {settings.odds_api_regions}\n"
        f"Odds markets: {settings.odds_api_markets}\n\n"
        f"NBA API: {nba_mode}\n"
        f"OpenAI/LLM: {openai_mode}\n"
        "Taxa analises sem odds: n/d\n"
        "Taxa matching odds baixa: n/d\n"
        f"Modo atual: {'ai_interpreter' if settings.openai_api_key else 'local_formatter'}\n\n"
        "Limitacoes: sem odds equivalentes, o bot nao classifica como value; com dados parciais, a confianca cai."
    )


def format_bet_advisor_response(advice: dict[str, Any]) -> str:
    return FootballResponseService().format_advice(advice)


def format_pre_match_card(card: dict[str, Any]) -> str:
    advice = card.get("advice") if isinstance(card, dict) else None
    if advice:
        return format_bet_advisor_response(advice)
    return str(card)


def format_value_response(value: dict[str, Any]) -> str:
    classification = value.get("classification") or value.get("confidence_level") or "sem value claro"
    odd = _optional_float(value.get("odd") or value.get("market_odd"))
    implied = _optional_float(value.get("implied_probability"))
    estimated = _optional_float(value.get("estimated_probability"))
    edge = _optional_float(value.get("edge"))

    lines = ["Value / Odd", ""]
    if odd:
        lines.append(f"Odd atual: {odd:.2f}")
    if implied is not None:
        lines.append(f"Probabilidade implicita: {_percent(implied)}")
    if estimated is not None:
        lines.append(f"Minha estimativa: {_percent(estimated)}")
    if edge is not None:
        lines.append(f"Edge: {_percent(edge)}")
    lines.extend(
        [
            f"Leitura: {classification}.",
            "",
            "Veredito: so considerar entrada se a odd compensar o risco. Probabilidade estimada nao e garantia.",
            "",
            "Use como apoio de analise, nao garantia. Aposte com gestao de banca.",
        ]
    )
    return "\n".join(lines)


def format_player_advice(player_advice: dict[str, Any]) -> str:
    player = player_advice.get("player") or "Jogador"
    lines = [
        "Minha leitura principal",
        "",
        f"Para {player}, o mercado que parece fazer mais sentido e:",
        str(player_advice.get("selection") or player_advice.get("main_market") or "dados insuficientes"),
        "",
        "Por que faz sentido:",
    ]
    lines.extend(_bullet_lines(player_advice.get("key_factors"), fallback="dados insuficientes para cravar uma prop"))
    lines.extend(["", "O que pode atrapalhar:"])
    lines.extend(_bullet_lines(player_advice.get("warnings"), fallback="minutos, titularidade e matchup precisam ser confirmados"))
    max_line = player_advice.get("max_line")
    if max_line not in (None, "", "dados insuficientes"):
        lines.extend(["", f"Linha maxima aceitavel: cuidado acima de {max_line}."])
    lines.extend(
        [
            "",
            "Eu evitaria:",
            f"- {player_advice.get('avoid', 'linhas muito acima da media recente')}",
            "",
            f"Veredito: {player_advice.get('final_verdict') or 'Eu so entraria com confirmacao de minutos e linha justa.'}",
            "",
            "Use como apoio de analise, nao garantia. Aposte com gestao de banca.",
        ]
    )
    return "\n".join(lines)


def format_top_props_advice(props: dict[str, Any]) -> str:
    best = props.get("best")
    if not best:
        return (
            "Minha leitura principal\n\n"
            "Eu nao vejo uma prop clara aqui.\n\n"
            f"Veredito: {props.get('final_verdict', 'Melhor nao forcar entrada pre-jogo.')}\n\n"
            "Use como apoio de analise, nao garantia. Aposte com gestao de banca."
        )

    lines = [
        "Minha leitura principal",
        "",
        f"Melhor nome para {props.get('market')}: {best.get('player')}",
        f"Selecao: {best.get('market')}",
        "",
        f"Motivo: {best.get('reason') or 'melhor equilibrio entre media, tendencia e risco no ranking.'}",
        "",
        "O que verificar antes:",
    ]
    lines.extend(_bullet_lines(props.get("warnings"), fallback="linha, titularidade e minutos projetados"))
    max_line = best.get("max_line")
    if max_line not in (None, "", "dados insuficientes"):
        lines.append(f"- Linha maxima aceitavel: cuidado se a casa subir muito acima de {max_line}.")
    lines.extend(
        [
            "",
            f"Veredito: {props.get('final_verdict') or 'Eu usaria como shortlist, nao como entrada automatica.'}",
            "",
            "Use como apoio de analise, nao garantia. Aposte com gestao de banca.",
        ]
    )
    return "\n".join(lines)


def format_bets_message(bets: list[Bet]) -> str:
    if not bets:
        return "Voce ainda nao registrou apostas."

    lines = ["Suas ultimas apostas:"]
    for bet in bets:
        lines.append(
            f"- #{bet.id} {bet.fixture_name} | {bet.market} | {bet.selection} | "
            f"odd {bet.odd:.2f} | stake {_money(bet.stake)} | {bet.status}"
        )
    return "\n".join(lines)


def format_betting_dashboard(
    open_bets: list[Bet],
    settled_bets: list[Bet],
    roi_data: dict[str, Any],
) -> str:
    lines = ["Minhas apostas", ""]
    lines.extend(
        [
            f"Lucro/prejuizo: {_money(roi_data.get('profit_loss', 0))}",
            f"Stake liquidada: {_money(roi_data.get('total_stake', 0))}",
            f"ROI: {_percent(roi_data.get('roi', 0))}",
            f"Taxa de acerto: {_percent(roi_data.get('win_rate', 0))}",
            f"Apostas encerradas: {roi_data.get('total_bets', 0)}",
            f"Abertas: {len(open_bets)}",
        ]
    )

    risk_note = _bankroll_note(roi_data, open_bets)
    if risk_note:
        lines.extend(["", f"Gestao: {risk_note}"])

    lines.append("")
    lines.append("Abertas:")
    if open_bets:
        for bet in open_bets[:8]:
            lines.append(_format_bet_line(bet, include_profit=False))
    else:
        lines.append("- Nenhuma aposta aberta.")

    lines.append("")
    lines.append("Ultimas encerradas:")
    if settled_bets:
        for bet in settled_bets[:8]:
            lines.append(_format_bet_line(bet, include_profit=True))
    else:
        lines.append("- Nenhuma aposta encerrada.")
    return "\n".join(lines)


def format_roi_message(roi_data: dict[str, Any]) -> str:
    return (
        "ROI e gestao\n"
        f"Apostas encerradas: {roi_data.get('total_bets', 0)}\n"
        f"Vitorias: {roi_data.get('won_bets', 0)} | Derrotas: {roi_data.get('lost_bets', 0)} | Voids: {roi_data.get('void_bets', 0)}\n"
        f"Taxa de acerto: {_percent(roi_data.get('win_rate', 0))}\n"
        f"Stake liquidada: {_money(roi_data.get('total_stake', 0))}\n"
        f"Lucro/prejuizo: {_money(roi_data.get('profit_loss', 0))}\n"
        f"ROI: {_percent(roi_data.get('roi', 0))}\n"
        f"Odd media: {_money(roi_data.get('average_odd', 0))}\n\n"
        "Leitura: use ROI junto com tamanho de amostra; poucas apostas ainda nao dizem muita coisa."
    )


def _format_bet_line(bet: Bet, *, include_profit: bool) -> str:
    base = (
        f"- #{bet.id} {bet.fixture_name} | {bet.market} | {bet.selection} | "
        f"odd {bet.odd:.2f} | stake {_money(bet.stake)} | {bet.status}"
    )
    if include_profit:
        base += f" | P/L {_money(bet.profit_loss or 0)}"
    elif bet.reason:
        base += f" | motivo: {bet.reason}"
    return base


def _bankroll_note(roi_data: dict[str, Any], open_bets: list[Bet]) -> str:
    if len(open_bets) >= 5:
        return "muitas apostas abertas; cuidado com exposicao acumulada."
    if roi_data.get("total_bets", 0) < 10:
        return "amostra pequena; priorize consistencia e stake baixa."
    if _optional_float(roi_data.get("roi")) is not None and float(roi_data.get("roi", 0)) < 0:
        return "ROI negativo; reduza stake ate estabilizar a leitura."
    return "sem alerta critico no momento."


def _bullet_lines(items: Any, fallback: str, limit: int = 5) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    if isinstance(items, str):
        return [f"- {items}"]
    return [f"- {item}" for item in list(items)[:limit]]


def _money(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "0.00%"
