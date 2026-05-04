from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"


@dataclass(frozen=True)
class MarketCandidate:
    key: str
    market: str
    selection: str
    score: float
    risk_points: float
    min_acceptable_odd: float | None
    reasons: list[str]
    risks: list[str]


class BetAdvisorService:
    """Transforms raw analysis into betting-oriented recommendations."""

    def advise_fixture_bets(self, fixture_analysis: dict[str, Any]) -> dict[str, Any]:
        fixture = fixture_analysis.get("fixture") or fixture_analysis
        home = fixture_analysis.get("home_team_data") or {}
        away = fixture_analysis.get("away_team_data") or {}
        context = fixture_analysis.get("context") or {}
        odds = _as_list(fixture_analysis.get("odds"))
        player_advice = fixture_analysis.get("player_advice") or {}
        football_context = fixture_analysis.get("football_context") or context.get("football_context") or {}

        candidates = self._score_football_markets(home, away, context, odds)
        candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
        prop_response = _prop_recommendation(fixture, player_advice, candidates, odds, football_context)
        if prop_response is not None:
            return prop_response

        if not candidates or candidates[0].score < 2.0:
            return self._no_clear_bet(fixture, candidates, home, away, context)

        main = candidates[0]
        alternatives = candidates[1:3]
        avoid = self._avoid_markets(candidates, home, away, context)
        value = _value_read(main, odds)
        estimated_probability = _estimated_probability(main.score, main.risk_points)
        warnings = _warnings_from_context(context, main.risks, odds)

        return {
            "fixture": fixture,
            "main_recommendation": {
                "market": main.market,
                "selection": main.selection,
                "confidence": _confidence(main.score, main.risk_points, value),
                "risk_level": _risk_level(main.risk_points, warnings),
                "min_acceptable_odd": main.min_acceptable_odd,
                "estimated_probability": estimated_probability,
                "fair_odd": _fair_odd(estimated_probability),
                "summary": _main_summary(fixture, main),
                "value": value,
                "odds_available": bool(odds),
                "odds_summary": _odds_summary(odds),
                "odds_note": _odds_note(main, odds, value),
            },
            "alternative_recommendations": [
                {
                    "market": item.market,
                    "selection": item.selection,
                    "confidence": _confidence(item.score, item.risk_points, None),
                    "reason": _short_reason(item),
                }
                for item in alternatives
            ],
            "avoid_markets": avoid,
            "key_factors": main.reasons[:4],
            "warnings": warnings[:4],
            "context_summary": football_context,
            "final_verdict": _final_verdict(fixture, main, value, warnings),
        }

    def advise_player_props(self, player_analysis: dict[str, Any]) -> dict[str, Any]:
        player = player_analysis.get("player") or player_analysis.get("name") or "Jogador"
        market = player_analysis.get("market") or player_analysis.get("mercado") or "prop"
        avg = _to_float(player_analysis.get("média_últimos_5") or player_analysis.get("media_ultimos_5"))
        risk = str(player_analysis.get("risco") or "médio")
        trend = str(player_analysis.get("tendência") or player_analysis.get("tendencia") or INSUFFICIENT_DATA)
        consistency = str(player_analysis.get("consistência") or player_analysis.get("consistencia") or INSUFFICIENT_DATA)

        warnings = ["confirme titularidade e minutos projetados"]
        if risk == "alto":
            warnings.append("entrada com risco alto por instabilidade da amostra")

        return {
            "player": player,
            "main_market": market,
            "selection": f"over em {market}" if avg is not None else market,
            "confidence": "média" if risk != "alto" and consistency in {"alta", "média"} else "baixa",
            "risk_level": risk,
            "max_line": round(avg, 2) if avg is not None else None,
            "key_factors": [
                f"média recente: {avg:.2f}" if avg is not None else "média recente indisponível",
                f"tendência: {trend}",
                f"consistência: {consistency}",
            ],
            "warnings": warnings,
            "avoid": "evitaria linhas acima da média recente sem melhora clara de minutos ou matchup",
            "final_verdict": (
                f"Eu só consideraria {player} em {market} se a linha estiver justa e a titularidade estiver confirmada."
            ),
        }

    def advise_top_props(self, ranking: list[dict[str, Any]], market: str) -> dict[str, Any]:
        if not ranking:
            return {
                "best": None,
                "market": market,
                "warnings": ["dados insuficientes para recomendar prop"],
                "final_verdict": "Minha recomendação aqui é não forçar entrada em props sem dados melhores.",
            }

        best = ranking[0]
        analysis = best.get("analysis") or {}
        return {
            "best": {
                "player": best.get("player"),
                "market": market,
                "confidence": "média" if analysis.get("risco") != "alto" else "baixa",
                "risk_level": analysis.get("risco", "médio"),
                "reason": analysis.get("leitura_para_aposta") or "melhor pontuação interna entre os jogadores analisados",
                "max_line": analysis.get("média_últimos_5") or analysis.get("média_geral"),
            },
            "alternatives": ranking[1:4],
            "warnings": ["verifique titularidade, minutos e linha oferecida pela casa"],
            "final_verdict": "Eu trataria o melhor nome como shortlist, não como entrada automática.",
        }

    def _score_football_markets(
        self,
        home: dict[str, Any],
        away: dict[str, Any],
        context: dict[str, Any],
        odds: list[dict[str, Any]],
    ) -> list[MarketCandidate]:
        home_scored = _num(home, "home_avg_scored", "avg_scored")
        home_conceded = _num(home, "home_avg_conceded", "avg_conceded")
        away_scored = _num(away, "away_avg_scored", "avg_scored")
        away_conceded = _num(away, "away_avg_conceded", "avg_conceded")
        home_last5_scored = _num(home, "last_5_avg_scored")
        home_last5_conceded = _num(home, "last_5_avg_conceded")
        away_last5_scored = _num(away, "last_5_avg_scored")
        away_last5_conceded = _num(away, "last_5_avg_conceded")
        home_form = _form_points(home.get("last_5_form"))
        away_form = _form_points(away.get("last_5_form"))

        candidates = [
            _score_home_win(home, away, home_scored, home_conceded, away_scored, away_conceded, home_form, away_form, context, odds),
            _score_home_dnb(home, away, home_scored, home_conceded, away_scored, away_conceded, home_form, away_form, context, odds),
            _score_over_15(home, away, home_scored, home_conceded, away_scored, away_conceded, context, odds),
            _score_over_25(home, away, home_scored, home_conceded, away_scored, away_conceded, context, odds),
            _score_btts(home, away, home_scored, home_conceded, away_scored, away_conceded, context, odds),
            _score_under_25(home, away, home_scored, home_conceded, away_scored, away_conceded, context, odds),
            _score_home_team_goal(home, away, home_scored, away_conceded, context, odds),
        ]
        candidates = [candidate for candidate in candidates if candidate is not None]
        _add_last5_context(candidates, home, away, home_last5_scored, home_last5_conceded, away_last5_scored, away_last5_conceded)
        return candidates

    def _avoid_markets(
        self,
        candidates: list[MarketCandidate],
        home: dict[str, Any],
        away: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, str]]:
        avoid = []
        home_name = _team_name(home, "Mandante")
        away_name = _team_name(away, "Visitante")
        home_conceded = _num(home, "home_avg_conceded", "avg_conceded")
        away_scored = _num(away, "away_avg_scored", "avg_scored")

        if home_conceded is not None and home_conceded >= 1.2:
            avoid.append(
                {
                    "market": f"vitória seca do {home_name} com odd baixa",
                    "reason": f"o {home_name} ainda sofre {home_conceded:.2f} gols em casa; a vitória simples pode carregar risco desnecessário.",
                }
            )
        if away_scored is not None and away_scored < 0.8:
            avoid.append(
                {
                    "market": f"gols do {away_name}",
                    "reason": f"o visitante produz pouco fora ({away_scored:.2f}); eu não forçaria esse lado sem escalação muito ofensiva.",
                }
            )
        if _context_risk(context):
            avoid.append(
                {
                    "market": "entradas fortes pré-jogo",
                    "reason": "há risco de rotação/contexto incompleto; melhor reduzir stake ou esperar escalações.",
                }
            )
        return avoid[:3]

    def _no_clear_bet(
        self,
        fixture: dict[str, Any],
        candidates: list[MarketCandidate],
        home: dict[str, Any],
        away: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        alternatives = candidates[:2]
        return {
            "fixture": fixture,
            "main_recommendation": {
                "market": "sem entrada clara pré-jogo",
                "selection": "evitar",
                "confidence": "baixa",
                "risk_level": "alto",
                "min_acceptable_odd": None,
                "estimated_probability": None,
                "fair_odd": None,
                "summary": "Os dados disponíveis não apontam uma vantagem forte o bastante para recomendar entrada.",
                "value": None,
            },
            "alternative_recommendations": [
                {
                    "market": item.market,
                    "selection": item.selection,
                    "confidence": "baixa",
                    "reason": _short_reason(item),
                }
                for item in alternatives
            ],
            "avoid_markets": self._avoid_markets(candidates, home, away, context),
            "key_factors": ["dados insuficientes ou conflitantes"],
            "warnings": ["melhor esperar escalações, odds e leitura inicial do jogo"],
            "context_summary": context.get("football_context") or {},
            "final_verdict": "Minha recomendação aqui é NÃO FORÇAR entrada pré-jogo. Se quiser atuar, eu olharia live com stake menor.",
        }


def _score_home_win(home, away, hs, hc, away_s, away_c, hf, af, context, odds):
    home_name = _team_name(home, "Mandante")
    score = 0.0
    risk = 0.0
    reasons = []
    risks = []
    if hs is not None and hs >= 1.5:
        score += 1.3
        reasons.append(f"{home_name} produz bem em casa ({hs:.2f} gols marcados).")
    if away_c is not None and away_c >= 1.5:
        score += 1.2
        reasons.append(f"visitante sofre bastante fora ({away_c:.2f}).")
    if hf is not None and af is not None and hf > af:
        score += 0.8
        reasons.append("forma recente do mandante é superior.")
    if hc is not None and hc >= 1.2:
        score -= 0.8
        risk += 1.0
        risks.append(f"{home_name} também concede gols em casa ({hc:.2f}).")
    if away_s is not None and away_s >= 1.0:
        score -= 0.5
        risk += 0.7
        risks.append("visitante tem alguma produção fora, então vitória seca fica menos confortável.")
    score, risk = _apply_context(score, risk, context, risks)
    odd = _find_odd(odds, ("home", "mandante", home_name))
    score, risk = _apply_odd(score, risk, odd, min_odd=1.75, reasons=reasons, risks=risks)
    return MarketCandidate("home_win", "Resultado", f"vitória do {home_name}", score, risk, 1.75, reasons, risks)


def _score_home_dnb(home, away, hs, hc, away_s, away_c, hf, af, context, odds):
    home_name = _team_name(home, "Mandante")
    score = 0.8
    risk = 0.3
    reasons = ["protege contra empate em jogo com algum risco no vencedor."]
    risks = []
    if hs is not None and hs >= 1.3:
        score += 0.8
        reasons.append(f"{home_name} tem produção aceitável em casa ({hs:.2f}).")
    if away_c is not None and away_c >= 1.4:
        score += 0.8
        reasons.append("defesa visitante concede espaços fora.")
    if hc is not None and hc >= 1.2:
        score += 0.3
        reasons.append("melhor que vitória seca porque o mandante também concede.")
    score, risk = _apply_context(score, risk, context, risks)
    return MarketCandidate("home_dnb", "Empate anula aposta", home_name, score, risk, 1.45, reasons, risks)


def _score_over_15(home, away, hs, hc, away_s, away_c, context, odds):
    score = 0.0
    risk = 0.2
    reasons = []
    risks = []
    total_signal = _sum_known(hs, away_s, hc, away_c)
    if total_signal is not None and total_signal >= 4.2:
        score += 1.2
        reasons.append("soma de produção ofensiva e gols sofridos aponta jogo com boa chance de pelo menos dois gols.")
    if hs is not None and hs >= 1.2 and away_c is not None and away_c >= 1.2:
        score += 1.0
        reasons.append("mandante tem caminho claro para contribuir no placar.")
    if away_s is not None and away_s >= 0.9 and hc is not None and hc >= 1.0:
        score += 0.8
        reasons.append("visitante também pode ajudar o over se o jogo abrir.")
    if total_signal is not None and total_signal < 3.0:
        score -= 1.0
        risk += 1.0
        risks.append("médias ofensivas não sustentam over com tanta folga.")
    score, risk = _apply_context(score, risk, context, risks)
    odd = _find_odd(odds, ("over 1.5", "over_1_5"))
    score, risk = _apply_odd(score, risk, odd, min_odd=1.35, reasons=reasons, risks=risks)
    return MarketCandidate("over_1_5_goals", "Total de gols", "Over 1.5 gols", score, risk, 1.35, reasons, risks)


def _score_over_25(home, away, hs, hc, away_s, away_c, context, odds):
    score = -0.2
    risk = 0.8
    reasons = []
    risks = ["precisa de jogo mais aberto; é mais sensível a escalação e odd."]
    total_signal = _sum_known(hs, away_s, hc, away_c)
    if total_signal is not None and total_signal >= 5.2:
        score += 1.7
        reasons.append("médias combinadas são fortes para cenário de três gols.")
    if hs is not None and away_s is not None and hs >= 1.4 and away_s >= 1.0:
        score += 0.8
        reasons.append("os dois ataques mostram capacidade de participação.")
    if total_signal is not None and total_signal < 4.2:
        score -= 0.8
        risks.append("não há folga estatística suficiente para over 2.5.")
    score, risk = _apply_context(score, risk, context, risks)
    return MarketCandidate("over_2_5_goals", "Total de gols", "Over 2.5 gols", score, risk, 1.85, reasons, risks)


def _score_btts(home, away, hs, hc, away_s, away_c, context, odds):
    score = 0.0
    risk = 0.5
    reasons = []
    risks = []
    if hs is not None and hs >= 1.2 and away_s is not None and away_s >= 1.0:
        score += 1.2
        reasons.append("os dois ataques têm produção mínima para participar do placar.")
    if hc is not None and hc >= 1.0 and away_c is not None and away_c >= 1.0:
        score += 1.0
        reasons.append("as duas defesas costumam conceder.")
    if away_s is not None and away_s < 0.8:
        score -= 1.0
        risk += 1.0
        risks.append("produção visitante fora é baixa.")
    score, risk = _apply_context(score, risk, context, risks)
    return MarketCandidate("both_teams_to_score", "Ambas marcam", "Sim", score, risk, 1.75, reasons, risks)


def _score_under_25(home, away, hs, hc, away_s, away_c, context, odds):
    score = 0.0
    risk = 0.5
    reasons = []
    risks = []
    total_signal = _sum_known(hs, away_s, hc, away_c)
    if total_signal is not None and total_signal <= 3.4:
        score += 1.6
        reasons.append("médias combinadas sugerem jogo mais controlado.")
    if hs is not None and hs < 1.2 and away_s is not None and away_s < 1.0:
        score += 1.0
        reasons.append("ataques não mostram volume alto.")
    if total_signal is not None and total_signal >= 4.8:
        score -= 1.6
        risk += 1.3
        risks.append("recortes de gols apontam mais para jogo aberto.")
    score, risk = _apply_context(score, risk, context, risks)
    return MarketCandidate("under_2_5_goals", "Total de gols", "Under 2.5 gols", score, risk, 1.75, reasons, risks)


def _score_home_team_goal(home, away, hs, away_c, context, odds):
    home_name = _team_name(home, "Mandante")
    score = 0.0
    risk = 0.2
    reasons = []
    risks = []
    if hs is not None and hs >= 1.2:
        score += 1.0
        reasons.append(f"{home_name} marca com frequência em casa ({hs:.2f}).")
    if away_c is not None and away_c >= 1.3:
        score += 1.0
        reasons.append(f"visitante sofre fora ({away_c:.2f}).")
    if hs is not None and hs < 1.0:
        score -= 1.0
        risks.append("produção do mandante em casa é baixa.")
    score, risk = _apply_context(score, risk, context, risks)
    return MarketCandidate("home_team_goals", "Gols do time", f"{home_name} over 0.5 gols", score, risk, 1.25, reasons, risks)


def _prop_recommendation(
    fixture: dict[str, Any],
    player_advice: dict[str, Any],
    candidates: list[MarketCandidate],
    odds: list[dict[str, Any]],
    football_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    best = player_advice.get("best") if isinstance(player_advice, dict) else None
    if not best:
        return None

    risk = str(best.get("risk_level") or "").lower()
    if risk in {"alto", "high"}:
        return None

    top_game_score = candidates[0].score if candidates else 0.0
    if top_game_score >= 2.8:
        return None

    selection = str(best.get("selection") or best.get("market") or "prop de jogador")
    player = str(best.get("player") or "jogador")
    warnings = list(best.get("warnings") or [])
    if not player_advice.get("lineups_confirmed"):
        warnings.append("titularidade ainda precisa ser confirmada.")
    if not odds:
        warnings.append("sem odds de props disponiveis, nao da para confirmar value.")

    estimated = 0.55 if risk in {"baixo", "low"} else 0.51
    return {
        "fixture": fixture,
        "main_recommendation": {
            "market": f"Prop de jogador - {best.get('market')}",
            "selection": f"{player}: {selection}",
            "confidence": "media" if risk in {"medio", "médio", "baixo"} else "baixa",
            "risk_level": "medio" if warnings else "baixo",
            "min_acceptable_odd": None,
            "estimated_probability": estimated,
            "fair_odd": _fair_odd(estimated),
            "summary": (
                f"O mercado de jogo nao ficou tao claro, entao eu olharia primeiro para {player} em {best.get('market')}. "
                "A leitura vem do volume individual e do risco menor em relacao aos mercados principais."
            ),
            "value": None,
            "odds_available": bool(odds),
            "odds_summary": _odds_summary(odds),
            "odds_note": "A Odds API nao retornou linha de prop equivalente para confirmar value.",
        },
        "alternative_recommendations": [
            {
                "market": item.market,
                "selection": item.selection,
                "confidence": _confidence(item.score, item.risk_points, None),
                "reason": _short_reason(item),
            }
            for item in candidates[:2]
        ],
        "avoid_markets": [
            {
                "market": "forcar vencedor pre-jogo",
                "reason": "a leitura por time nao ficou forte o bastante; a prop tem caminho mais especifico.",
            }
        ],
        "key_factors": list(best.get("reasons") or [])[:4],
        "warnings": _unique(warnings)[:4],
        "context_summary": football_context or {},
        "final_verdict": (
            f"Eu trataria {player} em {best.get('market')} como a melhor shortlist, mas so entraria com linha e odd justas."
        ),
    }


def _add_last5_context(
    candidates: list[MarketCandidate],
    home: dict[str, Any],
    away: dict[str, Any],
    home_scored: float | None,
    home_conceded: float | None,
    away_scored: float | None,
    away_conceded: float | None,
) -> None:
    home_name = _team_name(home, "Mandante")
    away_name = _team_name(away, "Visitante")
    context_parts = []
    if home_scored is not None and home_conceded is not None:
        context_parts.append(f"{home_name} nos últimos 5: {home_scored:.2f} gols feitos e {home_conceded:.2f} sofridos por jogo.")
    if away_scored is not None and away_conceded is not None:
        context_parts.append(f"{away_name} nos últimos 5: {away_scored:.2f} gols feitos e {away_conceded:.2f} sofridos por jogo.")
    if not context_parts:
        return

    for candidate in candidates:
        for item in context_parts:
            if item not in candidate.reasons:
                candidate.reasons.append(item)


def _main_summary(fixture: dict[str, Any], candidate: MarketCandidate) -> str:
    home = fixture.get("home_team") or "mandante"
    away = fixture.get("away_team") or "visitante"
    reason = _short_reason(candidate)
    return f"Para {home} x {away}, o mercado que parece mais favorável é {candidate.selection}. {reason}"


def _final_verdict(fixture: dict[str, Any], candidate: MarketCandidate, value: dict[str, Any] | None, warnings: list[str]) -> str:
    if value and value.get("classification") in {"value forte", "value moderado"}:
        return f"Eu consideraria {candidate.selection}, mas com gestão. A leitura esportiva e a odd parecem trabalhar a favor."
    if not value:
        return (
            f"Minha leitura é favorável para {candidate.selection}, mas eu só transformaria isso em entrada se a odd estiver aceitável "
            "e as escalações confirmarem o cenário."
        )
    return f"Eu gosto mais da leitura esportiva do que do preço. Se a odd estiver espremida, melhor evitar ou buscar alternativa mais segura."


def _value_read(candidate: MarketCandidate, odds: list[dict[str, Any]]) -> dict[str, Any] | None:
    odd = _find_candidate_odd(candidate, odds)
    if odd is None:
        return None
    estimated = _estimated_probability(candidate.score, candidate.risk_points)
    implied = 1 / odd if odd > 1 else 0
    edge = estimated - implied
    if edge > 0.07:
        classification = "value forte"
    elif edge > 0.04:
        classification = "value moderado"
    elif edge > 0.02:
        classification = "value leve"
    else:
        classification = "sem value claro"
    return {
        "odd": odd,
        "implied_probability": implied,
        "estimated_probability": estimated,
        "fair_odd": _fair_odd(estimated),
        "edge": edge,
        "classification": classification,
    }


def _find_candidate_odd(candidate: MarketCandidate, odds: list[dict[str, Any]]) -> float | None:
    if candidate.key == "over_2_5_goals":
        return _find_total_odd(odds, side="over", point=2.5)
    if candidate.key == "under_2_5_goals":
        return _find_total_odd(odds, side="under", point=2.5)
    if candidate.key == "home_win":
        return _find_h2h_odd(odds, candidate.selection.replace("vitória do ", ""))
    if candidate.key == "over_1_5_goals":
        return _find_total_odd(odds, side="over", point=1.5)
    return _find_odd(odds, (candidate.selection, candidate.market, candidate.key))


def _find_total_odd(odds: list[dict[str, Any]], side: str, point: float) -> float | None:
    for item in odds:
        market = str(item.get("market") or "").lower()
        selection = str(item.get("selection") or "").lower()
        item_point = _to_float(item.get("point"))
        if market == "totals" and selection == side and item_point is not None and abs(item_point - point) < 0.001:
            odd = _to_float(item.get("odd") or item.get("price") or item.get("decimal_odd"))
            if odd and odd > 1:
                return odd
    return None


def _find_h2h_odd(odds: list[dict[str, Any]], team_name: str) -> float | None:
    wanted = _normalize_text(team_name)
    for item in odds:
        market = str(item.get("market") or "").lower()
        selection = _normalize_text(item.get("selection"))
        if market == "h2h" and wanted and (wanted == selection or wanted in selection or selection in wanted):
            odd = _to_float(item.get("odd") or item.get("price") or item.get("decimal_odd"))
            if odd and odd > 1:
                return odd
    return None


def _odds_summary(odds: list[dict[str, Any]]) -> list[str]:
    lines = []
    seen = set()
    for item in odds:
        market = item.get("market")
        selection = item.get("selection")
        point = item.get("point")
        odd = _to_float(item.get("odd") or item.get("price") or item.get("decimal_odd"))
        if not market or not selection or not odd:
            continue
        label = f"{market} | {selection}"
        if point is not None:
            label += f" {point}"
        if label in seen:
            continue
        seen.add(label)
        lines.append(f"{label}: {odd:.2f}")
        if len(lines) >= 5:
            break
    return lines


def _odds_note(candidate: MarketCandidate, odds: list[dict[str, Any]], value: dict[str, Any] | None) -> str | None:
    if not odds:
        return None
    if value:
        return None
    if candidate.key == "over_1_5_goals":
        return "A Odds API retornou odds, mas não encontrei linha exata de Over 1.5. Muitas casas retornam apenas total 2.5."
    if candidate.key == "home_dnb":
        return "A Odds API retornou odds, mas não encontrei mercado de empate anula nesta chamada."
    if candidate.key == "home_team_goals":
        return "A Odds API retornou odds, mas não encontrei team total/gols do mandante nesta chamada."
    return "A Odds API retornou odds, mas não encontrei uma linha equivalente ao mercado recomendado."


def _estimated_probability(score: float, risk: float) -> float:
    return max(0.35, min(0.78, 0.48 + score * 0.045 - risk * 0.025))


def _fair_odd(probability: float | None) -> float | None:
    if probability is None or probability <= 0:
        return None
    return round(1 / probability, 2)


def _confidence(score: float, risk: float, value: dict[str, Any] | None) -> str:
    if risk >= 2.0 or score < 2.0:
        return "baixa"
    if value and value.get("classification") == "sem value claro":
        return "baixa"
    if score >= 3.4 and risk < 1.2:
        return "alta"
    return "média"


def _risk_level(risk: float, warnings: list[str]) -> str:
    if risk >= 2.0 or len(warnings) >= 3:
        return "alto"
    if risk >= 1.0 or warnings:
        return "médio"
    return "baixo"


def _warnings_from_context(context: dict[str, Any], risks: list[str], odds: list[dict[str, Any]]) -> list[str]:
    warnings = list(risks)
    if _context_risk(context):
        warnings.append("contexto indica possível rotação, fadiga ou informação incompleta.")
    if not odds:
        warnings.append("sem odds disponíveis, não dá para confirmar value.")
    warnings.append("confirme escalações e desfalques antes de entrar.")
    return _unique(warnings)


def _apply_context(score: float, risk: float, context: dict[str, Any], risks: list[str]) -> tuple[float, float]:
    if _context_risk(context):
        score -= 0.7
        risk += 1.0
        risks.append("contexto/escalação ainda pode mudar a leitura.")
    return score, risk


def _apply_odd(score: float, risk: float, odd: float | None, min_odd: float, reasons: list[str], risks: list[str]) -> tuple[float, float]:
    if odd is None:
        return score, risk
    if odd >= min_odd:
        score += 0.4
        reasons.append(f"odd {odd:.2f} não parece espremida para esta leitura.")
    else:
        score -= 0.8
        risk += 0.8
        risks.append(f"odd {odd:.2f} está baixa; pode já ter precificado a vantagem.")
    return score, risk


def _short_reason(candidate: MarketCandidate) -> str:
    return candidate.reasons[0] if candidate.reasons else "é o mercado com melhor equilíbrio entre leitura e risco."


def _context_risk(context: dict[str, Any]) -> bool:
    values = [
        str(context.get("rotation_risk") or "").lower(),
        str(context.get("fatigue_risk") or "").lower(),
        str(context.get("injuries") or "").lower(),
        str(context.get("alerts") or "").lower(),
    ]
    return any(word in " ".join(values) for word in ("alto", "médio", "medio", "rotação", "desfalque"))


def _find_odd(odds: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    lowered_terms = [_normalize_text(term) for term in terms if term]
    for item in odds:
        label = _normalize_text(" ".join(str(item.get(key, "")) for key in ("market", "selection", "name", "outcome")))
        if any(term and (term in label or _token_overlap(term, label)) for term in lowered_terms):
            odd = _to_float(item.get("odd") or item.get("price") or item.get("decimal_odd"))
            if odd and odd > 1:
                return odd
    return None


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    for token in ("vitória do", "vitoria do", "vitória da", "vitoria da", "over_", "_goals"):
        text = text.replace(token, " ")
    return " ".join(text.replace("_", " ").replace("-", " ").split())


def _token_overlap(left: str, right: str) -> bool:
    left_tokens = {token for token in left.split() if len(token) >= 4}
    right_tokens = {token for token in right.split() if len(token) >= 4}
    return bool(left_tokens & right_tokens)


def _sum_known(*values: float | None) -> float | None:
    known = [value for value in values if value is not None]
    if len(known) < 3:
        return None
    return sum(known)


def _num(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _to_float(data.get(key))
        if value is not None:
            return value
    return None


def _form_points(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    chars = [char.upper() for char in value if char.upper() in {"W", "D", "L", "V", "E"}][-5:]
    if not chars:
        return None
    points = 0
    for char in chars:
        if char in {"W", "V"}:
            points += 3
        elif char in {"D", "E"}:
            points += 1
    return points / (len(chars) * 3)


def _team_name(data: dict[str, Any], fallback: str) -> str:
    return str(data.get("name") or data.get("team_name") or fallback)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "items", "odds"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _unique(items: list[str]) -> list[str]:
    unique = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique


def advise_fixture_bets(fixture_analysis: dict[str, Any]) -> dict[str, Any]:
    return BetAdvisorService().advise_fixture_bets(fixture_analysis)
