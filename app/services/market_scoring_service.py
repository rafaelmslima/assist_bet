from __future__ import annotations

from typing import Any


def _label(score: int) -> str:
    if score >= 75:
        return "alta"
    if score >= 58:
        return "média"
    return "baixa"


class MarketScoringService:
    def score_markets(self, sport: str, signals: dict[str, Any], context: dict[str, Any], available_odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if sport == "football":
            return self._score_football(signals, context, available_odds)
        return self._score_nba(signals, context, available_odds)

    def _score_football(self, signals: dict[str, Any], context: dict[str, Any], available_odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        goals = int(signals.get("goals_trend_signal", 50))
        btts = int(signals.get("btts_signal", 50))
        under = int(signals.get("under_signal", 50))
        rotation_penalty = 12 if context.get("rotation_risk", 0) > 65 else 0
        markets = [
            self._mk("OVER_1_5_GOALS", "Over 1.5 gols", goals - rotation_penalty, ["Tendência de gols"], []),
            self._mk("OVER_2_5_GOALS", "Over 2.5 gols", goals - 8 - rotation_penalty, ["Linha mais agressiva"], []),
            self._mk("BTTS_YES", "Ambas marcam - Sim", btts - rotation_penalty, ["Ataques com produção"], []),
            self._mk("UNDER_2_5_GOALS", "Under 2.5 gols", under, ["Cenário mais controlado"], []),
            self._mk("HOME_WIN", "Mandante vence", int(signals.get("home_away_signal", 50)) - rotation_penalty, ["Força local"], ["Odd pode estar espremida"]),
        ]
        return [self._attach_odds(m, available_odds) for m in markets]

    def _score_nba(self, signals: dict[str, Any], context: dict[str, Any], available_odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pace = int(signals.get("goals_trend_signal", 50))
        fatigue = 10 if context.get("fatigue_risk", 0) > 70 else 0
        markets = [
            self._mk("GAME_TOTAL_OVER", "Total pontos over", pace - fatigue, ["Pace/ataque"], []),
            self._mk("GAME_TOTAL_UNDER", "Total pontos under", int(signals.get("under_signal", 50)), ["Defesa/ritmo"], []),
            self._mk("MONEYLINE_HOME", "Mandante ML", int(signals.get("home_away_signal", 50)) - fatigue, ["Fator casa"], []),
        ]
        return [self._attach_odds(m, available_odds) for m in markets]

    def _attach_odds(self, market: dict[str, Any], available_odds: list[dict[str, Any]]) -> dict[str, Any]:
        market["available_odd"] = None
        for item in available_odds:
            if str(item.get("key", "")).lower().startswith("h2h"):
                outcomes = item.get("outcomes") or []
                odd = outcomes[0].get("price") if outcomes else None
                if isinstance(odd, (int, float)):
                    market["available_odd"] = float(odd)
                    break
        return market

    def _mk(self, market: str, selection: str, score: int, reasons: list[str], warnings: list[str]) -> dict[str, Any]:
        score = max(0, min(100, score))
        risk = "alto" if score < 55 else "médio" if score < 75 else "baixo"
        return {
            "market": market,
            "selection": selection,
            "score": score,
            "confidence": _label(score),
            "risk": risk,
            "reasons": reasons,
            "warnings": warnings,
            "min_acceptable_odd": None,
            "available_odd": None,
            "has_value": None,
        }
