from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PresentationConfig:
    tone: str = "direct_conversation"
    length: str = "compact_plus"


class FootballResponseService:
    def __init__(self, config: PresentationConfig | None = None) -> None:
        self.config = config or PresentationConfig()

    def format_advice(self, advice: dict[str, Any]) -> str:
        fixture = advice.get("fixture") or {}
        main = advice.get("main_recommendation") or {}
        home = fixture.get("home_team") or fixture.get("home_team_name") or "Mandante"
        away = fixture.get("away_team") or fixture.get("away_team_name") or "Visitante"

        lines = [
            f"{home} x {away}",
            "",
            f"Ideia geral: {_compact(_clean(main.get('summary')) or _clean(advice.get('final_verdict')) or 'leitura parcial do confronto.', 140)}",
            f"Ideia de mercado: {self._entry_label(main)}",
            f"Motivo: {self._reason_line(main, advice)}",
            f"Riscos: {self._risk_line(main, advice)}",
        ]

        context = self._context_lines(advice.get("context_summary"))
        if context:
            lines.append("Contexto:")
            lines.extend(context[:2])

        alternatives = self._alternatives(advice.get("alternative_recommendations"), limit=2)
        lines.append("Ideias alternativas:")
        lines.extend(alternatives)
        lines.append("Evitaria:")
        lines.append(self._avoid_line(advice.get("avoid_markets")) or "forcar mercado sem confirmacao do roteiro.")
        return "\n".join(line for line in lines if line is not None)

    def _entry_label(self, main: dict[str, Any]) -> str:
        selection = str(main.get("selection") or "sem ideia forte")
        market = str(main.get("market") or "")
        if market and market.lower() not in selection.lower():
            return f"{selection} ({market})"
        return selection

    def _reason_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        reasons = main.get("reasons")
        if isinstance(reasons, list) and reasons:
            return _compact(_clean(reasons[0]), 110)
        return _compact(_clean(main.get("summary")) or _clean(advice.get("final_verdict")) or "dados ainda pedem cautela.", 110)

    def _risk_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        warnings = main.get("warnings") or advice.get("warnings") or []
        if isinstance(warnings, list) and warnings:
            return _compact(_clean(warnings[0]), 110)
        risk = main.get("risk_level") or main.get("risk")
        confidence = main.get("confidence")
        if risk or confidence:
            return f"risco {risk or 'medio'}, confianca {confidence or 'media'}."
        return "confirmar escalacoes, desfalques e contexto final."

    def _alternatives(self, alternatives: Any, limit: int = 3) -> list[str]:
        rows = []
        alt_list = [item for item in (alternatives or []) if isinstance(item, dict)]
        for idx in range(limit):
            if idx < len(alt_list):
                item = alt_list[idx]
                sel = str(item.get("selection") or item.get("market") or "alternativa")
                reason = _compact(_clean(item.get("reason")) or "linha secundaria para o mesmo cenario.", 70)
                rows.append(f"{idx + 1}. {sel} - {reason}")
            else:
                rows.append(f"{idx + 1}. Sem alternativa forte - melhor observar o jogo.")
        return rows

    def _avoid_line(self, avoid_markets: Any) -> str | None:
        avoid = [item for item in (avoid_markets or []) if isinstance(item, dict)]
        if not avoid:
            return None
        market = _clean(avoid[0].get("market"))
        reason = _compact(_clean(avoid[0].get("reason")), 70)
        if market and reason:
            return f"{market} - {reason}"
        return market or None

    def _context_lines(self, context_summary: Any) -> list[str]:
        if not isinstance(context_summary, dict):
            return []
        lines = context_summary.get("summary_lines") or []
        return [_clean(line) for line in lines if _clean(line)]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _compact(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;") + "."
