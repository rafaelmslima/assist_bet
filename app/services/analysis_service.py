from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"

FOOTBALL_MARKET_FIELDS = {
    "finalizações": ("shots", "avg_shots"),
    "finalizações_no_alvo": ("shots_on_target", "avg_shots_on_target"),
    "gols": ("goals", "avg_goals"),
    "assistências": ("assists", "avg_assists"),
    "desarmes": ("tackles", "avg_tackles"),
    "cartões": ("cards", "avg_cards"),
}

NBA_MARKET_FIELDS = {
    "pontos": ("points", "pts", "avg_points"),
    "rebotes": ("rebounds", "reb", "avg_rebounds"),
    "assistências": ("assists", "ast", "avg_assists"),
    "bolas_de_3": ("three_pointers", "fg3m", "avg_three_pointers"),
    "steals": ("steals", "stl", "avg_steals"),
    "blocks": ("blocks", "blk", "avg_blocks"),
    "PRA": ("pra", "avg_pra"),
}

MARKET_FIELDS = {**FOOTBALL_MARKET_FIELDS, **NBA_MARKET_FIELDS}


class AnalysisService:
    """Turns raw sports data into practical betting analysis."""

    def analyze_team(self, team_data: dict[str, Any]) -> dict[str, Any]:
        recent_values = _extract_recent_results(team_data)
        scored = _extract_number(team_data, "avg_scored", "goals_for_avg", "points_for_avg")
        conceded = _extract_number(team_data, "avg_conceded", "goals_against_avg", "points_against_avg")
        home_scored = _extract_number(team_data, "home_avg_scored", "home_points_for_avg")
        home_conceded = _extract_number(team_data, "home_avg_conceded", "home_points_against_avg")
        away_scored = _extract_number(team_data, "away_avg_scored", "away_points_for_avg")
        away_conceded = _extract_number(team_data, "away_avg_conceded", "away_points_against_avg")

        form = _classify_form(recent_values)
        offensive_strength = _classify_strength(scored, higher_is_better=True)
        defensive_strength = _classify_strength(conceded, higher_is_better=False)
        home_performance = _describe_split(home_scored, home_conceded)
        away_performance = _describe_split(away_scored, away_conceded)
        alerts = _team_alerts(team_data, recent_values, scored, conceded)

        return {
            "forma_recente": form,
            "força_ofensiva": offensive_strength,
            "força_defensiva": defensive_strength,
            "desempenho_casa": home_performance,
            "desempenho_fora": away_performance,
            "leitura_resumida": _team_summary(form, offensive_strength, defensive_strength),
            "alertas": alerts,
        }

    def analyze_matchup(
        self,
        home_team_data: dict[str, Any],
        away_team_data: dict[str, Any],
        fixture_context: dict[str, Any],
    ) -> dict[str, Any]:
        home_analysis = self.analyze_team(home_team_data)
        away_analysis = self.analyze_team(away_team_data)

        home_attack = _extract_number(home_team_data, "home_avg_scored", "avg_scored", "points_for_avg")
        home_defense = _extract_number(home_team_data, "home_avg_conceded", "avg_conceded", "points_against_avg")
        away_attack = _extract_number(away_team_data, "away_avg_scored", "avg_scored", "points_for_avg")
        away_defense = _extract_number(away_team_data, "away_avg_conceded", "avg_conceded", "points_against_avg")

        comparison = _compare_labels(home_analysis["forma_recente"], away_analysis["forma_recente"])
        home_attack_vs_away_defense = _attack_vs_defense(home_attack, away_defense)
        away_attack_vs_home_defense = _attack_vs_defense(away_attack, home_defense)
        home_away_edge = _home_away_edge(home_team_data, away_team_data)
        alerts = _matchup_alerts(fixture_context, home_analysis["alertas"], away_analysis["alertas"])

        matchup_read = _matchup_summary(
            comparison,
            home_attack_vs_away_defense,
            away_attack_vs_home_defense,
            home_away_edge,
        )

        return {
            "comparação_de_forma": comparison,
            "ataque_mandante_vs_defesa_visitante": home_attack_vs_away_defense,
            "ataque_visitante_vs_defesa_mandante": away_attack_vs_home_defense,
            "vantagem_casa_fora": home_away_edge,
            "leitura_de_matchup": matchup_read,
            "mercados_potenciais": _potential_markets(home_attack_vs_away_defense, away_attack_vs_home_defense),
            "alertas": alerts,
        }

    def analyze_player_props(self, player_stats: dict[str, Any], market_type: str) -> dict[str, Any]:
        values = _extract_market_values(player_stats, market_type)
        if not values:
            return _insufficient_player_prop(market_type)

        last_5 = values[-5:]
        general_avg = mean(values)
        last_5_avg = mean(last_5)
        trend = _trend(values)
        consistency = _consistency(values)
        risk = _risk_from_consistency_and_sample(consistency, len(values))

        return {
            "mercado": market_type,
            "média_geral": round(general_avg, 2),
            "média_últimos_5": round(last_5_avg, 2),
            "tendência": trend,
            "consistência": consistency,
            "risco": risk,
            "leitura_para_aposta": _player_prop_read(general_avg, last_5_avg, trend, consistency, risk),
        }

    def rank_top_props(
        self,
        players_stats: list[dict[str, Any]],
        market_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        ranked = []
        for player in players_stats:
            analysis = self.analyze_player_props(player, market_type)
            if analysis["média_geral"] == INSUFFICIENT_DATA:
                continue

            score = _prop_score(analysis)
            ranked.append(
                {
                    "player": player.get("name") or player.get("player_name") or INSUFFICIENT_DATA,
                    "market": market_type,
                    "score": round(score, 2),
                    "analysis": analysis,
                }
            )

        return sorted(ranked, key=lambda item: item["score"], reverse=True)[:limit]

    def generate_analysis_summary(self, data: dict[str, Any]) -> str:
        if not data:
            return INSUFFICIENT_DATA

        lines = []
        for key, value in data.items():
            if value in (None, "", [], {}):
                value = INSUFFICIENT_DATA
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value) if value else INSUFFICIENT_DATA
            lines.append(f"{_humanize_key(key)}: {value}")

        return "\n".join(lines[:8])

    def summarize_matchup(self, fixture: dict, context: dict, odds: list[dict]) -> dict:
        # TODO: Combine this with persisted analysis cards after API ingestion is implemented.
        return {
            "fixture": fixture,
            "context": context,
            "odds": odds,
            "summary": self.generate_analysis_summary(context),
        }


def _extract_number(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "."))
            except ValueError:
                continue
    return None


def _extract_recent_results(data: dict[str, Any]) -> list[str]:
    raw = data.get("recent_results") or data.get("last_5_form") or data.get("form")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [char.upper() for char in raw if char.upper() in {"W", "D", "L", "V", "E", "D"}]
    if isinstance(raw, list):
        return [str(item).upper() for item in raw]
    return []


def _classify_form(results: list[str]) -> str:
    if not results:
        return INSUFFICIENT_DATA

    points = 0
    for result in results[-5:]:
        if result in {"W", "V"}:
            points += 3
        elif result in {"D", "E"}:
            points += 1

    max_points = len(results[-5:]) * 3
    ratio = points / max_points if max_points else 0
    if ratio >= 0.67:
        return "forte"
    if ratio >= 0.4:
        return "regular"
    return "fraca"


def _classify_strength(value: float | None, *, higher_is_better: bool) -> str:
    if value is None:
        return INSUFFICIENT_DATA

    if higher_is_better:
        if value >= 2:
            return "forte"
        if value >= 1:
            return "regular"
        return "fraca"

    if value <= 1:
        return "forte"
    if value <= 2:
        return "regular"
    return "fraca"


def _describe_split(scored: float | None, conceded: float | None) -> str:
    if scored is None and conceded is None:
        return INSUFFICIENT_DATA

    scored_text = f"marca {scored:.2f}" if scored is not None else "ataque sem dados"
    conceded_text = f"sofre {conceded:.2f}" if conceded is not None else "defesa sem dados"
    return f"{scored_text}; {conceded_text}"


def _team_alerts(
    data: dict[str, Any],
    recent_results: list[str],
    scored: float | None,
    conceded: float | None,
) -> list[str]:
    alerts = []
    injuries = data.get("injuries") or data.get("injury_alerts")
    if injuries:
        alerts.append("atenção a desfalques")
    if recent_results and len(recent_results) < 5:
        alerts.append("amostra recente menor que 5 jogos")
    if scored is None or conceded is None:
        alerts.append(INSUFFICIENT_DATA)
    return alerts or ["sem alertas relevantes com os dados atuais"]


def _team_summary(form: str, attack: str, defense: str) -> str:
    if INSUFFICIENT_DATA in {form, attack, defense}:
        return INSUFFICIENT_DATA
    return f"Forma {form}, ataque {attack} e defesa {defense}."


def _compare_labels(home_label: str, away_label: str) -> str:
    if INSUFFICIENT_DATA in {home_label, away_label}:
        return INSUFFICIENT_DATA

    weights = {"fraca": 1, "regular": 2, "forte": 3}
    diff = weights[home_label] - weights[away_label]
    if diff > 0:
        return "mandante em melhor fase"
    if diff < 0:
        return "visitante em melhor fase"
    return "equilíbrio de forma"


def _attack_vs_defense(attack_avg: float | None, conceded_avg: float | None) -> str:
    if attack_avg is None or conceded_avg is None:
        return INSUFFICIENT_DATA

    combined = (attack_avg + conceded_avg) / 2
    if combined >= 2:
        return "cenário favorável ao ataque"
    if combined >= 1:
        return "cenário equilibrado"
    return "cenário travado"


def _home_away_edge(home_data: dict[str, Any], away_data: dict[str, Any]) -> str:
    home_scored = _extract_number(home_data, "home_avg_scored", "home_points_for_avg")
    away_scored = _extract_number(away_data, "away_avg_scored", "away_points_for_avg")
    if home_scored is None or away_scored is None:
        return INSUFFICIENT_DATA
    if home_scored > away_scored:
        return "mandante tem vantagem no recorte casa/fora"
    if away_scored > home_scored:
        return "visitante performa melhor fora"
    return "recorte casa/fora equilibrado"


def _matchup_alerts(context: dict[str, Any], home_alerts: list[str], away_alerts: list[str]) -> list[str]:
    alerts = []
    for key in ("injuries", "rotation", "rest_days", "travel", "motivation"):
        value = context.get(key)
        if value:
            alerts.append(f"{_humanize_key(key)}: {value}")
    alerts.extend(alert for alert in home_alerts + away_alerts if alert != "sem alertas relevantes com os dados atuais")
    return alerts or ["sem alertas relevantes com os dados atuais"]


def _matchup_summary(form: str, home_attack: str, away_attack: str, edge: str) -> str:
    values = [form, home_attack, away_attack, edge]
    if INSUFFICIENT_DATA in values:
        return INSUFFICIENT_DATA
    return f"{form}; {home_attack} para o mandante; {away_attack} para o visitante; {edge}."


def _potential_markets(home_attack: str, away_attack: str) -> list[str]:
    if INSUFFICIENT_DATA in {home_attack, away_attack}:
        return [INSUFFICIENT_DATA]
    markets = []
    if "favorável" in home_attack:
        markets.append("gols/pontos do mandante")
    if "favorável" in away_attack:
        markets.append("gols/pontos do visitante")
    if "travado" in home_attack and "travado" in away_attack:
        markets.append("unders")
    return markets or ["mercado principal apenas com cautela"]


def _extract_market_values(player_stats: dict[str, Any], market_type: str) -> list[float]:
    fields = MARKET_FIELDS.get(market_type)
    if fields is None:
        return []

    games = player_stats.get("games") or player_stats.get("recent_games") or player_stats.get("last_games")
    if isinstance(games, list):
        values = []
        for game in games:
            value = _extract_number(game, *fields)
            if value is not None:
                values.append(value)
        if market_type == "PRA" and not values:
            values = [_pra_from_game(game) for game in games]
            values = [value for value in values if value is not None]
        return values

    value = _extract_number(player_stats, *fields)
    if value is not None:
        return [value]
    return []


def _pra_from_game(game: dict[str, Any]) -> float | None:
    points = _extract_number(game, "points", "pts")
    rebounds = _extract_number(game, "rebounds", "reb")
    assists = _extract_number(game, "assists", "ast")
    if points is None or rebounds is None or assists is None:
        return None
    return points + rebounds + assists


def _trend(values: list[float]) -> str:
    if len(values) < 3:
        return INSUFFICIENT_DATA
    recent = mean(values[-3:])
    previous = mean(values[:-3]) if len(values) > 3 else values[0]
    if recent > previous * 1.1:
        return "alta"
    if recent < previous * 0.9:
        return "queda"
    return "estável"


def _consistency(values: list[float]) -> str:
    if len(values) < 3:
        return INSUFFICIENT_DATA
    avg = mean(values)
    if avg == 0:
        return "baixa"
    coefficient = pstdev(values) / avg
    if coefficient <= 0.25:
        return "alta"
    if coefficient <= 0.5:
        return "média"
    return "baixa"


def _risk_from_consistency_and_sample(consistency: str, sample_size: int) -> str:
    if sample_size < 5 or consistency == INSUFFICIENT_DATA:
        return "alto"
    if consistency == "alta":
        return "baixo"
    if consistency == "média":
        return "médio"
    return "alto"


def _player_prop_read(
    general_avg: float,
    last_5_avg: float,
    trend: str,
    consistency: str,
    risk: str,
) -> str:
    if trend == INSUFFICIENT_DATA or consistency == INSUFFICIENT_DATA:
        return INSUFFICIENT_DATA
    direction = "acima da média geral" if last_5_avg > general_avg else "abaixo ou alinhado à média geral"
    return f"Últimos 5 estão {direction}; tendência {trend}, consistência {consistency} e risco {risk}."


def _insufficient_player_prop(market_type: str) -> dict[str, Any]:
    return {
        "mercado": market_type,
        "média_geral": INSUFFICIENT_DATA,
        "média_últimos_5": INSUFFICIENT_DATA,
        "tendência": INSUFFICIENT_DATA,
        "consistência": INSUFFICIENT_DATA,
        "risco": INSUFFICIENT_DATA,
        "leitura_para_aposta": INSUFFICIENT_DATA,
    }


def _prop_score(analysis: dict[str, Any]) -> float:
    trend_bonus = {"alta": 2, "estável": 1, "queda": -1}.get(analysis["tendência"], 0)
    consistency_bonus = {"alta": 2, "média": 1, "baixa": -1}.get(analysis["consistência"], 0)
    risk_penalty = {"baixo": 0, "médio": 1, "alto": 2}.get(analysis["risco"], 2)
    return float(analysis["média_últimos_5"]) + trend_bonus + consistency_bonus - risk_penalty


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()
