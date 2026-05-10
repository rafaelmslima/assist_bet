from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
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
            self._general_read_line(main, advice),
            f"Melhor entrada: {self._entry_label(main)}",
            f"Motivo: {self._reason_line(main, advice)}",
            f"Riscos: {self._risk_line(main, advice)}",
            self._price_line(main, advice),
        ]

        context = self._context_lines(advice.get("context_summary"))
        if context:
            lines.append("Contexto:")
            lines.extend(context[:2])

        alternatives = self._alternatives(advice.get("alternative_recommendations"), limit=2)
        lines.append("Alternativas:")
        lines.extend(alternatives)
        lines.append("Evitaria:")
        lines.append(self._avoid_line(advice.get("avoid_markets")) or "forcar entrada pre-jogo sem vantagem clara.")
        verdict = _compact(_clean(advice.get("final_verdict")), 120)
        if verdict:
            lines.append(f"Veredito: {verdict}")

        return "\n".join(line for line in lines if line is not None)

    def _general_read_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        if _is_avoid(main):
            return "Leitura geral: pre-jogo sem vantagem clara para entrar."
        summary = _clean(main.get("summary")) or _clean(advice.get("final_verdict"))
        if summary:
            return f"Leitura geral: {_compact(summary, 120)}"
        return "Leitura geral: ha uma direcao, mas a entrada depende de preco e contexto."

    def _entry_label(self, main: dict[str, Any]) -> str:
        if _is_avoid(main):
            return "sem entrada pre-jogo"
        selection = str(main.get("selection") or "entrada coletiva")
        market = str(main.get("market") or "")
        if market and market.lower() not in selection.lower():
            return f"{selection} ({market})"
        return selection

    def _reason_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        reasons = main.get("reasons")
        if isinstance(reasons, list) and reasons:
            return _compact(_clean(reasons[0]), 110)
        return _compact(_clean(main.get("summary")) or _clean(advice.get("final_verdict")) or "sem edge claro no momento.", 110)

    def _risk_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        warnings = main.get("warnings") or advice.get("warnings") or []
        if isinstance(warnings, list) and warnings:
            return _compact(_clean(warnings[0]), 110)
        risk = main.get("risk_level") or main.get("risk")
        confidence = main.get("confidence")
        if risk or confidence:
            return f"risco {risk or 'medio'}, confianca {confidence or 'media'}."
        return "confirme escalacoes, desfalques e odds antes de entrar."

    def _price_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        value = main.get("value")
        if isinstance(value, dict):
            odd = _float_or_none(value.get("odd"))
            fair = _float_or_none(value.get("fair_odd") or main.get("fair_odd"))
            classification = value.get("classification") or "value indefinido"
            if odd and fair:
                return f"Preco: odd {odd:.2f}, justa {fair:.2f}, {classification}."

        market = _norm(main.get("market"))
        odds_note = _clean(main.get("odds_note"))
        warnings = " ".join(str(item) for item in (advice.get("warnings") or []))
        if "prop" in market and ("sem odds" in _norm(warnings) or "linha de prop" in _norm(odds_note) or "props" in _norm(odds_note)):
            return "Preco/value: sem linha equivalente para props."
        if odds_note:
            return f"Preco/value: {_compact(odds_note, 100)}"
        return "Preco/value: sem linha equivalente para confirmar value."

    def _read_paragraph(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        intro = self._opening_line(main)
        reason = _compact(_clean(main.get("summary")) or _clean((advice.get("final_verdict") or "")), 120)
        context = self._context_hint(advice.get("context_summary"))
        parts = [intro]
        if reason:
            parts.append(reason)
        if context:
            parts.append(context)
        return " ".join(parts)

    def _opening_line(self, main: dict[str, Any]) -> str:
        if _is_avoid(main):
            return "Leitura do jogo: pre-jogo sem entrada clara."
        return "Leitura do jogo: ha uma direcao mais confiavel no mercado coletivo."

    def _best_bet_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        if _is_avoid(main):
            return "Sem aposta clara - os sinais estao fracos ou instaveis."
        selection = str(main.get("selection") or "entrada coletiva")
        market = str(main.get("market") or "mercado")
        selection_label = selection if market.lower() in selection.lower() else f"{selection} ({market})"
        reason = _compact(_clean(main.get("summary")) or _clean((advice.get("key_factors") or [""])[0]), 90)
        odds_note = self._odds_note(main, advice)
        if odds_note:
            return f"{selection_label} - {reason} {odds_note}".strip()
        return f"{selection_label} - {reason}".strip()

    def _alternatives(self, alternatives: Any, limit: int = 3) -> list[str]:
        rows = []
        alt_list = [item for item in (alternatives or []) if isinstance(item, dict)]
        for idx in range(limit):
            if idx < len(alt_list):
                item = alt_list[idx]
                sel = str(item.get("selection") or item.get("market") or "alternativa")
                reason = _compact(_clean(item.get("reason")) or "linha secundaria para o mesmo cenario.", 60)
                rows.append(f"{idx + 1}. {sel} - {reason}")
            else:
                rows.append(f"{idx + 1}. Sem alternativa forte - melhor esperar mercado/live.")
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

    def _context_hint(self, context_summary: Any) -> str:
        if not isinstance(context_summary, dict):
            return ""
        lines = context_summary.get("summary_lines") or []
        cleaned = [_clean(line) for line in lines if _clean(line)]
        if not cleaned:
            return ""
        return _compact(" ".join(cleaned[:2]), 130)

    def _context_lines(self, context_summary: Any) -> list[str]:
        if not isinstance(context_summary, dict):
            return []
        lines = context_summary.get("summary_lines") or []
        return [_clean(line) for line in lines if _clean(line)]

    def _odds_note(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        value = main.get("value")
        if isinstance(value, dict):
            odd = _float_or_none(value.get("odd"))
            fair = _float_or_none(value.get("fair_odd") or main.get("fair_odd"))
            if odd and fair:
                return f"(odd {odd:.2f}; justa {fair:.2f})."
        warnings = " ".join(str(item) for item in (advice.get("warnings") or []))
        if "sem odds" in _norm(warnings) or "linha equivalente" in _norm(warnings):
            return "(sem odd equivalente para confirmar value)."
        return ""


def _is_avoid(main: dict[str, Any]) -> bool:
    return _norm(main.get("selection")) == "evitar" or "sem entrada" in _norm(main.get("market"))


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _compact(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;") + "."


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
