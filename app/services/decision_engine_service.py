from __future__ import annotations

from typing import Any


class DecisionEngineService:
    def build_recommendation(self, fixture_context: dict[str, Any]) -> dict[str, Any]:
        fixture = fixture_context.get("fixture", {})
        sport = fixture_context.get("sport", "football")
        archetype = fixture_context.get("archetype", {})
        markets = sorted(fixture_context.get("market_scores", []), key=lambda m: m.get("score", 0), reverse=True)
        traps = fixture_context.get("traps", {})
        data_quality = fixture_context.get("signals", {}).get("data_quality", "média")
        main = markets[0] if markets else None
        should_avoid = traps.get("should_avoid_pre_match", False) or not main or main.get("score", 0) < 58
        if should_avoid:
            main = {
                "market": "NO_BET",
                "selection": "Não apostar pré-jogo",
                "score": 0,
                "confidence": "baixa",
                "risk": "alto",
                "reasons": ["Leitura sem edge claro"],
                "warnings": traps.get("traps", []),
                "min_acceptable_odd": None,
                "available_odd": None,
                "has_value": None,
            }
        confidence = "alta" if main.get("score", 0) >= 75 else "média" if main.get("score", 0) >= 58 else "baixa"
        risk = "baixo" if main.get("score", 0) >= 75 else "médio" if main.get("score", 0) >= 58 else "alto"
        return {
            "fixture": fixture,
            "sport": sport,
            "archetype": archetype,
            "main_recommendation": main,
            "alternative_recommendations": [m for m in markets[1:4] if m.get("score", 0) >= 50 and m.get("market") != main.get("market")],
            "avoid_markets": [m for m in markets if m.get("score", 0) < 50][:3],
            "traps": traps.get("traps", []),
            "confidence": confidence,
            "risk": risk,
            "stake_suggestion": "não apostar" if should_avoid else "baixa" if confidence == "média" else "média",
            "should_bet_pre_match": not should_avoid,
            "should_wait_live": should_avoid or main.get("available_odd") is None,
            "data_quality": data_quality,
            "final_verdict": "Não apostar pré-jogo." if should_avoid else f"Melhor leitura: {main.get('selection')}.",
            "raw_signals": fixture_context.get("signals", {}),
        }
