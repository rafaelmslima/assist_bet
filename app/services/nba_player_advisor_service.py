from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MARKETS = {
    "points": ("pontos", "pts", "season_pts", "player_points"),
    "rebounds": ("rebotes", "reb", "season_reb", "player_rebounds"),
    "assists": ("assistencias", "ast", "season_ast", "player_assists"),
    "threes": ("bolas de 3", "fg3m", "season_fg3m", "player_threes"),
    "pra": ("PRA", "pra", "season_pra", "player_points_rebounds_assists"),
}


@dataclass(frozen=True)
class NbaPropCandidate:
    player: dict[str, Any]
    market_key: str
    market: str
    stat_value: float
    score: float
    risk: float
    reasons: list[str]
    warnings: list[str]


class NbaPlayerAdvisorService:
    """Ranks NBA player props and formats advisor-ready output."""

    def advise_game_props(self, context: Any, odds: list[dict[str, Any]] | None = None, limit: int = 5) -> dict[str, Any]:
        odds = odds or []
        candidates = []
        for player in getattr(context, "players", []) or []:
            if player.get("injury_status"):
                continue
            candidates.extend(_player_candidates(player))

        candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
        selected = _dedupe_players(candidates)[:limit]
        if not selected:
            return {
                "game": getattr(context, "game", {}) or {},
                "best": None,
                "recommendations": [],
                "data_quality": getattr(context, "data_quality", []) or [],
                "final_verdict": "Eu nao vejo prop clara com os dados disponiveis. Melhor esperar status, linhas e minutos projetados.",
            }

        return {
            "game": getattr(context, "game", {}) or {},
            "best": _candidate_to_dict(selected[0], odds),
            "recommendations": [_candidate_to_dict(item, odds) for item in selected],
            "data_quality": getattr(context, "data_quality", []) or [],
            "final_verdict": _verdict(selected[0]),
        }


def format_nba_prop_advice(advice: dict[str, Any]) -> str:
    game = advice.get("game") or {}
    home = game.get("home_team") or "Mandante"
    away = game.get("visitor_team") or "Visitante"
    lines = [f"🏀 NBA Props - {away} @ {home}", ""]
    best = advice.get("best")

    if not best:
        lines.extend(
            [
                "Eu nao encontrei uma prop confiavel para esse jogo.",
                "",
                "Por que:",
            ]
        )
        lines.extend(f"- {item}" for item in (advice.get("data_quality") or ["dados insuficientes"])[:4])
        lines.extend(["", f"Veredito: {advice.get('final_verdict')}"])
        return "\n".join(lines)

    lines.extend(
        [
            "Melhor leitura:",
            f"{best.get('player')} - {best.get('selection')}",
            f"Confiança: {best.get('confidence')} | Risco: {best.get('risk_level')}",
            "",
            "Motivo:",
        ]
    )
    lines.extend(f"- {item}" for item in (best.get("reasons") or [])[:4])

    if best.get("value"):
        value = best["value"]
        lines.extend(
            [
                "",
                "Odds / value:",
                f"Odd atual: {value['odd']:.2f}",
                f"Probabilidade implícita: {value['implied_probability'] * 100:.2f}%",
                f"Minha estimativa: {value['estimated_probability'] * 100:.2f}%",
                f"Odd justa: {value['fair_odd']:.2f}",
                f"Leitura: {value['classification']}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Odds / value:",
                "Sem linha de prop equivalente na Odds API. A leitura é esportiva, não confirmação de value.",
            ]
        )

    warnings = best.get("warnings") or []
    if warnings:
        lines.extend(["", "Riscos:"])
        lines.extend(f"- {item}" for item in warnings[:3])

    alternatives = advice.get("recommendations") or []
    if len(alternatives) > 1:
        lines.extend(["", "Alternativas:"])
        for item in alternatives[1:5]:
            lines.append(f"- {item.get('player')}: {item.get('selection')} ({item.get('risk_level')})")

    lines.extend(
        [
            "",
            "Eu evitaria:",
            "- Forçar prop de jogador com status indefinido ou linha muito acima da média recente.",
            "",
            "Veredito:",
            str(advice.get("final_verdict")),
            "",
            "Use como apoio de análise, não como garantia. Aposte com gestão de banca.",
        ]
    )
    return "\n".join(lines)


def _player_candidates(player: dict[str, Any]) -> list[NbaPropCandidate]:
    candidates = []
    recent = player.get("recent_metrics") or {}
    matchup = player.get("matchup") or {}
    position = str(player.get("position") or "").upper()
    minutes = _first_number(recent.get("min"), player.get("season_min"))

    for market_key, (label, recent_key, season_key, _odds_market) in MARKETS.items():
        if market_key == "pra":
            recent_value = _sum_known(recent.get("pts"), recent.get("reb"), recent.get("ast"))
            season_value = _sum_known(player.get("season_pts"), player.get("season_reb"), player.get("season_ast"))
        else:
            recent_value = _to_float(recent.get(recent_key))
            season_value = _to_float(player.get(season_key))

        value = _first_number(recent_value, season_value)
        if value is None or value <= 0:
            continue

        score = value / _market_divisor(market_key)
        risk = 0.4
        reasons = [f"média recente/base em {label}: {value:.2f}."]
        warnings = []

        if recent_value is not None and season_value is not None and recent_value > season_value * 1.08:
            score += 0.8
            reasons.append("últimos jogos estão acima da média de temporada.")
        if minutes is not None and minutes >= 30:
            score += 0.8
            reasons.append(f"minutagem forte ({minutes:.1f} min).")
        elif minutes is not None and minutes < 24:
            risk += 1.0
            warnings.append(f"minutagem baixa ou instável ({minutes:.1f} min).")
        else:
            risk += 0.5
            warnings.append("minutos projetados precisam ser confirmados.")

        if market_key == "assists" and position.startswith("G"):
            score += 0.4
            reasons.append("posição de guard ajuda leitura de assistências.")
        if market_key == "rebounds" and ("C" in position or position.startswith("F")):
            score += 0.5
            reasons.append("posição favorece rebotes.")
        if market_key == "threes" and position.startswith("G"):
            score += 0.4
            reasons.append("perfil de guard favorece bolas de 3.")

        score += float(matchup.get("score") or 0)
        reasons.extend(matchup.get("factors") or [])
        warnings.extend(matchup.get("warnings") or [])

        if market_key == "pra":
            consistency = recent.get("consistency")
            if consistency == "baixa":
                risk += 0.8
                warnings.append("PRA fica mais arriscado quando a produção recente oscila muito.")

        if score - risk * 0.25 < 1.2:
            continue

        candidates.append(
            NbaPropCandidate(
                player=player,
                market_key=market_key,
                market=label,
                stat_value=value,
                score=score - risk * 0.25,
                risk=risk,
                reasons=_unique(reasons),
                warnings=_unique(warnings),
            )
        )
    return candidates


def _candidate_to_dict(candidate: NbaPropCandidate, odds: list[dict[str, Any]]) -> dict[str, Any]:
    player = candidate.player
    odd = _find_prop_odd(candidate, odds)
    estimated = _estimated_probability(candidate.score, candidate.risk)
    value = None
    if odd:
        implied = 1 / odd
        edge = estimated - implied
        value = {
            "odd": odd,
            "implied_probability": implied,
            "estimated_probability": estimated,
            "fair_odd": round(1 / estimated, 2),
            "edge": edge,
            "classification": _value_classification(edge),
        }

    return {
        "player": player.get("player_name"),
        "team": player.get("team_name"),
        "market": candidate.market,
        "selection": _selection(candidate),
        "stat_value": round(candidate.stat_value, 2),
        "confidence": _confidence(candidate.score, candidate.risk, value),
        "risk_level": _risk(candidate.risk),
        "reasons": candidate.reasons,
        "warnings": candidate.warnings,
        "value": value,
    }


def _selection(candidate: NbaPropCandidate) -> str:
    if candidate.market_key == "pra":
        return f"PRA, se a linha estiver perto de {max(1.5, candidate.stat_value - 2):.1f}"
    return f"over em {candidate.market}, se a linha estiver perto de {max(0.5, candidate.stat_value - 1):.1f}"


def _find_prop_odd(candidate: NbaPropCandidate, odds: list[dict[str, Any]]) -> float | None:
    player_name = _norm(candidate.player.get("player_name"))
    odds_market = MARKETS[candidate.market_key][3]
    for item in odds:
        if str(item.get("market")) != odds_market:
            continue
        selection = _norm(item.get("selection") or item.get("description") or item.get("name"))
        if player_name and (player_name in selection or selection in player_name):
            odd = _to_float(item.get("odd") or item.get("price"))
            if odd and odd > 1:
                return odd
    return None


def _dedupe_players(candidates: list[NbaPropCandidate]) -> list[NbaPropCandidate]:
    selected = []
    seen = set()
    for candidate in candidates:
        key = str(candidate.player.get("player_id") or candidate.player.get("player_name"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
    return selected


def _verdict(candidate: NbaPropCandidate) -> str:
    player = candidate.player.get("player_name") or "esse jogador"
    return f"Eu olharia primeiro para {player} em {candidate.market}, mas só entraria se status e linha confirmarem a leitura."


def _estimated_probability(score: float, risk: float) -> float:
    return max(0.42, min(0.66, 0.49 + score * 0.035 - risk * 0.02))


def _value_classification(edge: float) -> str:
    if edge > 0.07:
        return "value forte"
    if edge > 0.04:
        return "value moderado"
    if edge > 0.02:
        return "value leve"
    return "sem value claro"


def _confidence(score: float, risk: float, value: dict[str, Any] | None) -> str:
    if risk >= 2.0 or score < 1.5:
        return "baixa"
    if value and value.get("classification") == "sem value claro":
        return "baixa"
    if score >= 2.8 and risk < 1.0:
        return "alta"
    return "media"


def _risk(risk: float) -> str:
    if risk >= 2.0:
        return "alto"
    if risk >= 1.0:
        return "medio"
    return "baixo"


def _market_divisor(market_key: str) -> float:
    return {"points": 9, "rebounds": 4, "assists": 3.5, "threes": 1.5, "pra": 15}.get(market_key, 5)


def _sum_known(*values: Any) -> float | None:
    known = [_to_float(value) for value in values]
    known = [value for value in known if value is not None]
    return sum(known) if len(known) == len(values) else None


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = _to_float(value)
        if parsed is not None:
            return parsed
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _unique(items: list[str]) -> list[str]:
    unique = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique
