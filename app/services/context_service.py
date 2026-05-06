from __future__ import annotations

from typing import Any


class ContextService:
    def build_football_context(self, fixture_context: dict[str, Any]) -> dict[str, Any]:
        warnings = []
        if fixture_context.get("lineup_unconfirmed"):
            warnings.append("Escalacao indefinida")
        if fixture_context.get("rotation_risk", 0) > 65:
            warnings.append("Risco de rotacao")
        return {
            "fatigue_risk": fixture_context.get("fatigue_risk", 40),
            "rotation_risk": fixture_context.get("rotation_risk", 40),
            "motivation_level": fixture_context.get("motivation_level", 60),
            "lineup_risk": 70 if fixture_context.get("lineup_unconfirmed") else 35,
            "context_warnings": warnings,
            "context_summary": fixture_context.get("context_summary", "Contexto padrao"),
        }

    def build_nba_context(self, fixture_context: dict[str, Any]) -> dict[str, Any]:
        warnings = []
        if fixture_context.get("back_to_back"):
            warnings.append("Back-to-back")
        return {
            "fatigue_risk": 75 if fixture_context.get("back_to_back") else 45,
            "rotation_risk": fixture_context.get("rotation_risk", 45),
            "motivation_level": fixture_context.get("motivation_level", 60),
            "lineup_risk": 70 if fixture_context.get("lineup_unconfirmed") else 40,
            "context_warnings": warnings,
            "context_summary": fixture_context.get("context_summary", "Contexto NBA"),
        }
