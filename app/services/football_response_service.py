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

        context = self._context_lines(advice.get("context_summary"))
        alternatives = self._alternatives(advice.get("alternative_recommendations"), limit=2)
        avoid = self._avoid_line(advice.get("avoid_markets")) or "forçar mercado sem confirmação do roteiro"
        summary = _clean(main.get("summary")) or _clean(advice.get("final_verdict")) or "os dados ainda deixam a leitura parcial"
        entry = self._entry_label(main)
        risk = self._risk_line(main, advice)

        lines = [f"{home} x {away}", ""]
        lines.append(f"A leitura aqui é que {summary[0].lower() + summary[1:] if summary else 'o confronto ainda pede cautela.'}")
        if context:
            lines.append(f"O contexto pesa porque {_compact(' '.join(context[:2]), 180)}")
        lines.append(f"Como ideia de mercado, eu olharia primeiro para {entry}. O ponto de cuidado é {risk[0].lower() + risk[1:] if risk else 'confirmar as informações finais do jogo.'}")
        if alternatives:
            lines.append(f"Se quiser uma segunda leitura, {alternatives}. Evitaria {avoid}.")
        else:
            lines.append(f"Evitaria {avoid}.")
        return "\n\n".join(line for line in lines if line)

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

    def _alternatives(self, alternatives: Any, limit: int = 3) -> str:
        rows = []
        alt_list = [item for item in (alternatives or []) if isinstance(item, dict)]
        for idx in range(limit):
            if idx < len(alt_list):
                item = alt_list[idx]
                sel = str(item.get("selection") or item.get("market") or "alternativa")
                reason = _compact(_clean(item.get("reason")) or "linha secundaria para o mesmo cenario.", 70)
                rows.append(f"{sel} ({reason})")
        return _natural_join(rows)

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


def _natural_join(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} ou {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} ou {cleaned[-1]}"
