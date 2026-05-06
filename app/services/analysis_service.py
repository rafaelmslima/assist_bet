from __future__ import annotations

from typing import Any


def _clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


class AnalysisService:
    # Compatibilidade com serviços legados:
    def analyze_team(self, team_data: dict[str, Any]) -> dict[str, Any]:
        avg_scored = float(team_data.get("avg_scored", 1.2))
        avg_conceded = float(team_data.get("avg_conceded", 1.2))
        return {"strength": _clamp((avg_scored - avg_conceded + 2) * 25), "team": team_data.get("name")}

    def analyze_matchup(self, home: dict[str, Any], away: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "edge_home": _clamp((float(home.get("avg_scored", 1.2)) - float(away.get("avg_conceded", 1.2)) + 2) * 25),
            "edge_away": _clamp((float(away.get("avg_scored", 1.2)) - float(home.get("avg_conceded", 1.2)) + 2) * 25),
            "context": context,
        }

    def analyze_football(self, fixture_context: dict[str, Any]) -> dict[str, Any]:
        home = fixture_context.get("home_stats", {})
        away = fixture_context.get("away_stats", {})
        hg = float(home.get("avg_scored", 1.2))
        hc = float(home.get("avg_conceded", 1.1))
        ag = float(away.get("avg_scored", 1.1))
        ac = float(away.get("avg_conceded", 1.2))
        goals_trend = _clamp(((hg + ag + hc + ac) / 6.0) * 100)
        btts = _clamp(((hg + ag) / 4.0) * 100)
        under = _clamp(100 - goals_trend + 10)
        return {
            "form_signal": _clamp((float(home.get("form_points", 7)) + float(away.get("form_points", 7))) * 7),
            "home_away_signal": _clamp((hg - ag + 1.5) * 30),
            "attack_signal": _clamp((hg + ag) * 28),
            "defense_signal": _clamp((2.4 - (hc + ac) / 2) * 40),
            "goals_trend_signal": goals_trend,
            "btts_signal": btts,
            "under_signal": under,
            "shots_signal": _clamp(float(home.get("shots", 10)) * 4 + float(away.get("shots", 9)) * 3),
            "corners_signal": _clamp(float(home.get("corners", 5)) * 8 + float(away.get("corners", 4)) * 7),
            "cards_signal": _clamp(float(home.get("cards", 2)) * 15 + float(away.get("cards", 2)) * 15),
            "consistency_signal": _clamp((float(home.get("consistency", 55)) + float(away.get("consistency", 55))) / 2),
            "data_quality": fixture_context.get("data_quality", "média"),
        }

    def analyze_nba(self, fixture_context: dict[str, Any]) -> dict[str, Any]:
        h = fixture_context.get("home_stats", {})
        a = fixture_context.get("away_stats", {})
        pace = (float(h.get("pace", 98)) + float(a.get("pace", 98))) / 2
        total = float(h.get("pts_for", 112)) + float(a.get("pts_for", 110))
        return {
            "form_signal": _clamp((float(h.get("form_points", 6)) + float(a.get("form_points", 6))) * 8),
            "home_away_signal": _clamp((float(h.get("home_edge", 0.1)) + 1) * 45),
            "attack_signal": _clamp(total / 3),
            "defense_signal": _clamp((240 - float(h.get("pts_against", 111)) - float(a.get("pts_against", 112))) * 2),
            "goals_trend_signal": _clamp(total / 3),
            "btts_signal": 50,
            "under_signal": _clamp(100 - (total / 3)),
            "shots_signal": _clamp(pace),
            "corners_signal": 0,
            "cards_signal": 0,
            "consistency_signal": _clamp((float(h.get("consistency", 55)) + float(a.get("consistency", 55))) / 2),
            "data_quality": fixture_context.get("data_quality", "média"),
        }
