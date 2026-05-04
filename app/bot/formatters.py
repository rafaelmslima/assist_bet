from __future__ import annotations

from typing import Any

from app.config import settings
from app.database.models import Bet


def format_start_message() -> str:
    return (
        "Bem-vindo ao Sports Betting Assistant.\n\n"
        "Escolha uma função no teclado para começar sua análise."
    )


def format_help_message() -> str:
    return (
        "Escolha uma opção no teclado fixo para iniciar uma consulta.\n\n"
        "Você pode analisar jogos, times, jogadores, odds, value betting, registrar apostas "
        "e consultar seu histórico."
    )


def format_status_message() -> str:
    api_key_status = "configurada" if settings.api_football_key else "ausente"
    odds_key_status = "configurada" if settings.odds_api_key else "ausente"
    api_mode = "RapidAPI" if "rapidapi.com" in settings.api_football_base_url else "API-Sports direto"
    return (
        "Bot online. Banco local configurado.\n\n"
        f"API-Football key: {api_key_status}\n"
        f"Modo API-Football: {api_mode}\n"
        f"Base URL: {settings.api_football_base_url}\n\n"
        f"Odds API key: {odds_key_status}\n"
        f"Odds regions: {settings.odds_api_regions}\n"
        f"Odds markets: {settings.odds_api_markets}"
    )


def format_bet_advisor_response(advice: dict[str, Any]) -> str:
    fixture = advice.get("fixture") or {}
    home = fixture.get("home_team") or fixture.get("home_team_name") or "Mandante"
    away = fixture.get("away_team") or fixture.get("away_team_name") or "Visitante"
    main = advice.get("main_recommendation") or {}
    value = main.get("value")
    return _format_compact_bet_advisor_response(advice, fixture, home, away, main, value)

    lines = [
        f"🎯 {home} x {away}",
        "",
        f"Melhor aposta: {main.get('market', 'Mercado')} - {main.get('selection', 'seleção')}",
        f"Confiança: {main.get('confidence', 'baixa')} | Risco: {main.get('risk_level', 'médio')}",
        "",
        "O que eu faria:",
        str(main.get("summary") or "Os dados disponíveis apontam melhor equilíbrio entre potencial e risco neste mercado."),
        "",
        "Por que faz sentido:",
    ]
    lines.extend(_bullet_lines(advice.get("key_factors"), fallback="dados ainda limitados para sustentar leitura forte", limit=3))

    lines.extend(["", "Riscos:"])
    lines.extend(_bullet_lines(advice.get("warnings"), fallback="odds e escalações precisam ser confirmadas", limit=2))

    lines.extend(["", "Odds e preço:"])
    lines.extend(_format_value_block(value, main))

    alternatives = advice.get("alternative_recommendations") or []
    if alternatives:
        lines.extend(["", "Alternativas:"])
        for index, item in enumerate(alternatives[:3], start=1):
            lines.append(f"{index}. {item.get('market')} - {item.get('selection')}: {item.get('reason')}")

    avoid = advice.get("avoid_markets") or []
    if avoid:
        lines.extend(["", "Eu evitaria:"])
        for item in avoid[:2]:
            lines.append(f"- {item.get('market')}")
            lines.append(f"Motivo: {item.get('reason')}")

    lines.extend(
        [
            "",
            "Veredito final:",
            str(advice.get("final_verdict") or "Eu não forçaria entrada sem confirmar odds e escalações."),
        ]
    )
    return "\n".join(lines)


def format_pre_match_card(card: dict[str, Any]) -> str:
    advice = card.get("advice") if isinstance(card, dict) else None
    if advice:
        return format_bet_advisor_response(advice)
    return str(card)


def _format_compact_bet_advisor_response(
    advice: dict[str, Any],
    fixture: dict[str, Any],
    home: str,
    away: str,
    main: dict[str, Any],
    value: dict[str, Any] | None,
) -> str:
    lines = [
        f"{home} x {away}",
        "",
        f"Melhor aposta: {main.get('selection', 'evitar')} ({main.get('market', 'mercado')})",
    ]

    summary = main.get("summary")
    if summary:
        lines.append(f"Motivo: {summary}")
    else:
        reasons = _plain_limited_lines(
            advice.get("key_factors"),
            fallback="Dados ainda limitados para sustentar leitura forte.",
            limit=2,
        )
        lines.append(f"Motivo: {' '.join(reasons)}")

    lines.extend(["", "Contexto:"])
    lines.extend(_context_lines(advice.get("context_summary")))

    lines.extend(["", "Odds/preco:"])
    lines.extend(_format_value_block(value, main)[:3])

    alternatives = advice.get("alternative_recommendations") or []
    if alternatives:
        lines.extend(["", "Alternativas:"])
        for item in alternatives[:2]:
            reason = item.get("reason")
            suffix = f" - {reason}" if reason else ""
            lines.append(f"- {item.get('selection')} ({item.get('market')}){suffix}")

    avoid = advice.get("avoid_markets") or []
    lines.extend(["", "Evitaria:"])
    if avoid:
        item = avoid[0]
        reason = item.get("reason")
        lines.append(f"{item.get('market')}" + (f" - {reason}" if reason else ""))
    else:
        lines.append("Entrada forte sem confirmar odds e escalacoes.")

    lines.extend(
        [
            "",
            f"Veredito: {advice.get('final_verdict') or 'Eu nao forcaria entrada sem confirmar odds e escalacoes.'}",
            "",
            "Use como apoio, nao garantia. Aposte com gestao de banca.",
        ]
    )
    return "\n".join(lines)


def format_value_response(value: dict[str, Any]) -> str:
    classification = value.get("classification") or value.get("confidence_level") or "sem value claro"
    odd = _optional_float(value.get("odd") or value.get("market_odd"))
    implied = _optional_float(value.get("implied_probability"))
    estimated = _optional_float(value.get("estimated_probability"))
    edge = _optional_float(value.get("edge"))

    lines = ["💰 Value / Odd", ""]
    if odd:
        lines.append(f"Odd atual: {odd:.2f}")
    if implied is not None:
        lines.append(f"Probabilidade implícita: {_percent(implied)}")
    if estimated is not None:
        lines.append(f"Minha estimativa: {_percent(estimated)}")
    if edge is not None:
        lines.append(f"Edge: {_percent(edge)}")
    lines.append(f"Leitura: {classification}.")
    lines.extend(
        [
            "",
            "✅ Veredito",
            "Eu só consideraria entrada se a odd compensar o risco. Probabilidade estimada não é garantia.",
            "",
            "Use como apoio de análise, não como garantia. Aposte com gestão de banca.",
        ]
    )
    return "\n".join(lines)


def format_player_advice(player_advice: dict[str, Any]) -> str:
    player = player_advice.get("player") or "Jogador"
    lines = [
        "🎯 Minha leitura principal",
        "",
        f"Para {player}, o mercado que parece fazer mais sentido é:",
        f"{player_advice.get('selection') or player_advice.get('main_market')}",
        "",
        "📊 Por que essa leitura faz sentido",
    ]
    lines.extend(_bullet_lines(player_advice.get("key_factors"), fallback="dados insuficientes para cravar uma prop"))
    lines.extend(["", "⚠️ O que pode atrapalhar"])
    lines.extend(_bullet_lines(player_advice.get("warnings"), fallback="minutos, titularidade e matchup precisam ser confirmados"))
    max_line = player_advice.get("max_line")
    if max_line not in (None, "", "dados insuficientes"):
        lines.extend(["", f"Linha máxima aceitável: eu teria cautela acima de {max_line}."])
    lines.extend(
        [
            "",
            "🚫 Eu evitaria",
            f"- {player_advice.get('avoid', 'linhas muito acima da média recente')}",
            "",
            "✅ Veredito",
            str(player_advice.get("final_verdict") or "Eu só entraria com confirmação de minutos e linha justa."),
            "",
            "Use como apoio de análise, não como garantia. Aposte com gestão de banca.",
        ]
    )
    return "\n".join(lines)


def format_top_props_advice(props: dict[str, Any]) -> str:
    best = props.get("best")
    if not best:
        return (
            "🎯 Minha leitura principal\n\n"
            "Eu não vejo uma prop clara aqui.\n\n"
            "✅ Veredito\n"
            f"{props.get('final_verdict', 'Melhor não forçar entrada pré-jogo.')}\n\n"
            "Use como apoio de análise, não como garantia. Aposte com gestão de banca."
        )

    lines = [
        "🎯 Minha leitura principal",
        "",
        f"Melhor nome para {props.get('market')}: {best.get('player')}",
        f"Seleção: {best.get('market')}",
        "",
        "Motivo:",
        str(best.get("reason") or "é o melhor equilíbrio entre média, tendência e risco no ranking."),
        "",
        "⚠️ O que verificar antes",
    ]
    lines.extend(_bullet_lines(props.get("warnings"), fallback="linha, titularidade e minutos projetados"))
    max_line = best.get("max_line")
    if max_line not in (None, "", "dados insuficientes"):
        lines.append(f"- Linha máxima aceitável: cuidado se a casa subir muito acima de {max_line}.")
    lines.extend(
        [
            "",
            "✅ Veredito",
            str(props.get("final_verdict") or "Eu usaria como shortlist, não como entrada automática."),
            "",
            "Use como apoio de análise, não como garantia. Aposte com gestão de banca.",
        ]
    )
    return "\n".join(lines)


def _format_value_block(value: dict[str, Any] | None, main: dict[str, Any]) -> list[str]:
    estimated = _optional_float(main.get("estimated_probability"))
    fair_odd = _optional_float(main.get("fair_odd"))
    if not value:
        probability_lines = []
        if estimated is not None:
            probability_lines.append(f"Minha probabilidade estimada: {_percent(estimated)}")
        if fair_odd is not None:
            probability_lines.append(f"Odd justa estimada: {fair_odd:.2f}")

        if main.get("odds_available"):
            lines = probability_lines + ["Odds encontradas na API, mas sem linha equivalente exata para o mercado recomendado."]
            note = main.get("odds_note")
            if note:
                lines.append(str(note))
            summary = main.get("odds_summary") or []
            if summary:
                lines.append("Algumas odds disponíveis:")
                lines.extend(f"- {item}" for item in summary[:5])
            return lines

        min_odd = main.get("min_acceptable_odd")
        if min_odd:
            return probability_lines + [
                "Sem odds disponíveis, não dá para confirmar value.",
                f"Pela leitura esportiva, eu só consideraria se a odd estiver acima de {float(min_odd):.2f}.",
            ]
        return probability_lines + ["Sem odds disponíveis, não dá para confirmar value. A leitura esportiva favorece este mercado."]

    return [
        f"Odd atual: {float(value.get('odd')):.2f}",
        f"Probabilidade implícita: {_percent(value.get('implied_probability'))}",
        f"Minha estimativa: {_percent(value.get('estimated_probability'))}",
        f"Odd justa estimada: {_optional_float(value.get('fair_odd')):.2f}",
        f"Edge: {_percent(value.get('edge'))}",
        f"Leitura: {value.get('classification')}.",
    ]


def _bullet_lines(items: Any, fallback: str, limit: int = 5) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    if isinstance(items, str):
        return [f"- {items}"]
    return [f"- {item}" for item in list(items)[:limit]]


def _plain_limited_lines(items: Any, fallback: str, limit: int = 2) -> list[str]:
    if not items:
        return [fallback]
    if isinstance(items, str):
        return [items]
    values = [str(item) for item in list(items)[:limit] if item]
    return values or [fallback]


def _context_lines(context_summary: Any) -> list[str]:
    if not isinstance(context_summary, dict):
        return ["Contexto indisponivel."]
    lines = context_summary.get("summary_lines") or []
    if not lines:
        return ["Contexto indisponivel."]
    return [str(item) for item in lines[:2] if item] or ["Contexto indisponivel."]


def format_bets_message(bets: list[Bet]) -> str:
    if not bets:
        return "Você ainda não registrou apostas."

    lines = ["Suas últimas apostas:"]
    for bet in bets:
        lines.append(
            f"- {bet.fixture_name} | {bet.market} | {bet.selection} | odd {bet.odd:.2f} | stake {bet.stake:.2f} | {bet.status}"
        )
    return "\n".join(lines)


def format_betting_dashboard(
    open_bets: list[Bet],
    settled_bets: list[Bet],
    roi_data: dict[str, Any],
) -> str:
    lines = ["Minhas apostas"]
    lines.append("")
    lines.append("Abertas:")
    if open_bets:
        for bet in open_bets[:10]:
            lines.append(_format_bet_line(bet, include_profit=False))
    else:
        lines.append("- Nenhuma aposta aberta.")

    lines.append("")
    lines.append("Últimas encerradas:")
    if settled_bets:
        for bet in settled_bets[:10]:
            lines.append(_format_bet_line(bet, include_profit=True))
    else:
        lines.append("- Nenhuma aposta encerrada.")

    lines.append("")
    lines.append(
        f"Lucro/prejuízo: {_money(roi_data.get('profit_loss', 0))}\n"
        f"Stake liquidada: {_money(roi_data.get('total_stake', 0))}\n"
        f"ROI: {_percent(roi_data.get('roi', 0))}"
    )
    return "\n".join(lines)


def format_roi_message(roi_data: dict[str, Any]) -> str:
    return (
        "ROI básico\n"
        f"Apostas encerradas: {roi_data.get('total_bets', 0)}\n"
        f"Stake liquidada: {_money(roi_data.get('total_stake', 0))}\n"
        f"Lucro/prejuízo: {_money(roi_data.get('profit_loss', 0))}\n"
        f"ROI: {_percent(roi_data.get('roi', 0))}"
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
