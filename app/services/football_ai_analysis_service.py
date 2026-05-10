from __future__ import annotations

from typing import Any

from app.integrations.openai_client import OpenAIClient


class FootballAIAnalysisService:
    """Delegates the final football recommendation to the AI."""

    def __init__(self, client: OpenAIClient | None = None) -> None:
        self.client = client or OpenAIClient()

    def analyze(self, dossier: dict[str, Any]) -> dict[str, Any]:
        text = self.client.analyze_football_dossier(dossier)
        if text:
            return {
                "advisor_text": _trim_telegram_text(text),
                "mode": "football_ai",
                "dossier": dossier,
            }
        return {
            "advisor_text": self._fallback(dossier),
            "mode": "football_ai_fallback",
            "dossier": dossier,
        }

    def _fallback(self, dossier: dict[str, Any]) -> str:
        fixture = dossier.get("fixture") or {}
        home = fixture.get("home_team") or "Mandante"
        away = fixture.get("away_team") or "Visitante"
        quality = dossier.get("data_quality") or {}
        notes = quality.get("notes") or []
        reason = notes[0] if notes else "a IA nao esta configurada ou nao respondeu."
        candidates = dossier.get("market_candidates") or []
        live = next((item for item in candidates if item.get("key") == "wait_live_or_no_bet"), {})
        confidence = "baixa" if quality.get("level") != "completo" else "media"

        where = "live, apos confirmar ritmo/escalações."
        if live.get("signal") == "baixo":
            where = "pre-jogo somente se a IA estiver ativa para validar o dossie."

        return "\n".join(
            [
                f"{home} x {away}",
                "",
                "Melhor decisao: sem entrada pre-jogo.",
                f"Motivo: {reason}",
                f"Onde olhar: {where}",
                "",
                "Evitaria:",
                "forcar aposta sem analise da IA.",
                "",
                f"Confianca: {confidence}",
            ]
        )


def _trim_telegram_text(text: str, max_lines: int = 14) -> str:
    lines = [line.rstrip() for line in str(text).strip().splitlines()]
    return "\n".join(lines[:max_lines]).strip()
