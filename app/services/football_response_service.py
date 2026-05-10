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

        lines = [f"{home} x {away}", "", self._read_paragraph(main, advice), "", "Melhor aposta:"]
        lines.append(self._best_bet_line(main, advice))
        lines.append("")
        lines.append("Boas alternativas:")
        lines.extend(self._alternatives(advice.get("alternative_recommendations")))
        lines.append("")
        lines.append("Evitaria:")
        lines.append(self._avoid_line(advice.get("avoid_markets")) or "forcar entrada pre-jogo sem vantagem clara.")

        compact = [line for line in lines if line is not None]
        return "\n".join(compact[:12])

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

    def _alternatives(self, alternatives: Any) -> list[str]:
        rows = []
        alt_list = [item for item in (alternatives or []) if isinstance(item, dict)]
        for idx in range(3):
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
