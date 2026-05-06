from __future__ import annotations


class TrapDetectionService:
    def detect(self, context: dict, markets: list[dict], archetype: dict) -> dict:
        traps: list[str] = []
        if context.get("rotation_risk", 0) > 70:
            traps.append("Risco alto de rotação")
        if context.get("lineup_risk", 0) > 70:
            traps.append("Escalação indefinida")
        if archetype.get("archetype") == "AVOID_PRE_MATCH":
            traps.append("Contexto não favorece pré-jogo")
        low_value = [m for m in markets if m.get("available_odd") and m.get("score", 0) < 58]
        if low_value:
            traps.append("Mercados sem value claro")
        severity = "high" if len(traps) >= 2 else "medium" if traps else "low"
        return {"traps": traps, "severity": severity, "should_avoid_pre_match": severity == "high"}
