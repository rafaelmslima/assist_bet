from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.integrations.openai_client import OpenAIClient
from app.schemas.football_ai import FootballAIAnalysis


logger = logging.getLogger(__name__)


class FootballAIAnalysisService:
    """Delegates the final football recommendation to the AI."""

    def __init__(self, client: OpenAIClient | None = None) -> None:
        self.client = client or OpenAIClient()

    def analyze(self, dossier: dict[str, Any]) -> dict[str, Any]:
        raw_response = self.client.analyze_football_dossier(dossier)
        analysis = _parse_ai_analysis(raw_response)
        if analysis:
            return {
                "advisor_text": _format_analysis(analysis),
                "mode": "football_ai",
                "dossier": dossier,
                "analysis": analysis.model_dump(),
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
        targets = dossier.get("probability_targets") or []

        return "\n".join(
            [
                f"{home} x {away}",
                "",
                "Probabilidades estimadas:",
                *_fallback_probability_lines(targets),
                "",
                "Leitura do jogo:",
                f"Sem IA ativa, eu nao vou inventar percentuais finais. O principal limitador agora e: {reason}",
                "",
                "Possivel entrada:",
                "sem entrada pre-jogo - falta estimativa probabilistica final da IA para comparar com as odds.",
                "",
                "Evitaria:",
                "forcar aposta apenas com leitura parcial dos dados.",
            ]
        )


def _parse_ai_analysis(raw_response: str | None) -> FootballAIAnalysis | None:
    if not raw_response:
        return None
    try:
        payload = json.loads(raw_response)
        return FootballAIAnalysis.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning("Invalid football AI analysis response: %s", exc.__class__.__name__)
        return None


def _format_analysis(analysis: FootballAIAnalysis) -> str:
    probability_lines = []
    ordered = {
        item.market_key: item
        for item in analysis.probabilities
    }
    for key in (
        "over_1_5_goals",
        "over_2_5_goals",
        "home_over_0_5_goals",
        "away_over_0_5_goals",
        "favorite_win",
        "corners",
    ):
        item = ordered[key]
        if item.data_status == "dados_insuficientes" or item.probability_percent is None:
            probability_lines.append(f"- {item.label}: dados insuficientes | confianca {item.confidence}")
        else:
            probability_lines.append(f"- {item.label}: {item.probability_percent}% | confianca {item.confidence}")

    entry = analysis.possible_entry
    value_note = ""
    if entry.has_confirmed_value and entry.min_acceptable_odd:
        value_note = f" | odd minima {entry.min_acceptable_odd:.2f}"
    elif not entry.has_confirmed_value:
        value_note = " | sem value confirmado"

    return "\n".join(
        [
            analysis.fixture_label,
            "",
            "Probabilidades estimadas:",
            *probability_lines,
            "",
            "Leitura do jogo:",
            analysis.match_reading,
            "",
            "Possivel entrada:",
            f"{entry.label} - {entry.reason}{value_note}",
            "",
            "Evitaria:",
            analysis.avoid,
        ]
    )


def _fallback_probability_lines(targets: list[dict[str, Any]]) -> list[str]:
    labels = {
        "over_1_5_goals": "Over 1.5 gols",
        "over_2_5_goals": "Over 2.5 gols",
        "home_over_0_5_goals": "Gol do mandante",
        "away_over_0_5_goals": "Gol do visitante",
        "favorite_win": "Vitoria do favorito",
        "corners": "Escanteios",
    }
    by_key = {item.get("key"): item for item in targets if isinstance(item, dict)}
    rows = []
    for key, label in labels.items():
        target = by_key.get(key) or {}
        probability = target.get("base_probability_hint")
        confidence = target.get("confidence_hint") or "baixa"
        if probability is None:
            rows.append(f"- {label}: dados insuficientes | confianca baixa")
        else:
            rows.append(f"- {label}: {probability * 100:.0f}% base | confianca {confidence}")
    return rows
