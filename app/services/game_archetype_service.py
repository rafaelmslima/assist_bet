from __future__ import annotations


class GameArchetypeService:
    def classify(self, sport: str, signals: dict, context: dict, has_odds: bool) -> dict:
        if context.get("lineup_risk", 0) > 75:
            return {"archetype": "AVOID_PRE_MATCH", "confidence": 78, "why": ["Escalacao indefinida"]}
        if sport == "football":
            if signals.get("goals_trend_signal", 50) > 64:
                return {"archetype": "OPEN_GAME", "confidence": 72, "why": ["Tendencia de gols"]}
            if signals.get("under_signal", 50) > 62:
                return {"archetype": "UNDER_GAME", "confidence": 68, "why": ["Ritmo mais travado"]}
            return {"archetype": "BALANCED_GAME", "confidence": 60, "why": ["Sinais equilibrados"]}
        if signals.get("goals_trend_signal", 50) > 64:
            return {"archetype": "HIGH_PACE_GAME", "confidence": 70, "why": ["Pace projetado alto"]}
        if not has_odds:
            return {"archetype": "AVOID_PRE_MATCH", "confidence": 66, "why": ["Sem odds para validar value"]}
        return {"archetype": "BALANCED_SPREAD", "confidence": 58, "why": ["Leitura sem dominancia clara"]}
