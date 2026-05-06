from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"


@dataclass(frozen=True)
class PresentationConfig:
    tone: str = "direct_conversation"
    length: str = "compact_plus"
    show_context: str = "always"
    show_alternatives: str = "always"
    show_warnings: str = "conditional"
    show_odds_note: str = "conditional"


class FootballResponseService:
    """Builds the football advisory response sent to Telegram."""

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
            self._decision_line(main),
            self._risk_line(main),
            f"A ideia: {self._main_reason(main, advice)}",
            "",
            "Contexto:",
            *self._context_lines(advice.get("context_summary")),
            "Alternativas:",
            *self._alternatives(advice.get("alternative_recommendations")),
        ]

        avoid = self._avoid_line(advice.get("avoid_markets"))
        if avoid:
            lines.append(f"Eu evitaria: {avoid}")

        warnings = self._warning_line(advice.get("warnings"), advice.get("context_summary"))
        if warnings:
            lines.append(f"Antes de entrar: {warnings}")

        odds_note = self._odds_observation(main, advice)
        if odds_note:
            lines.append(f"Obs. odds: {odds_note}")

        lines.append(f"Veredito: {self._verdict(advice, main)}")
        return "\n".join(str(line) for line in lines if line is not None)

    def _decision_line(self, main: dict[str, Any]) -> str:
        market = str(main.get("market") or "mercado")
        selection = str(main.get("selection") or "evitar")
        if _is_avoid(main):
            return "Eu nao entraria pre-jogo aqui. Sem entrada pre-jogo."
        return f"Eu iria por {selection} ({market})."

    def _risk_line(self, main: dict[str, Any]) -> str:
        confidence = _normalize_label(main.get("confidence") or "baixa")
        risk = _normalize_label(main.get("risk_level") or "medio")
        management = _stake_phrase(main)
        price = _price_phrase(main)
        if price:
            return f"Confianca {confidence}, risco {risk}. {management} {price}"
        return f"Confianca {confidence}, risco {risk}. {management}"

    def _main_reason(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        summary = _clean_sentence(main.get("summary"))
        if summary:
            return _compact_summary(summary)
        factors = [_clean_sentence(item) for item in _as_text_list(advice.get("key_factors"), limit=2)]
        factors = [item for item in factors if item]
        if factors:
            return " ".join(factors)
        return "os dados atuais nao mostram uma vantagem clara o bastante nos mercados principais."

    def _context_lines(self, context_summary: Any) -> list[str]:
        if not isinstance(context_summary, dict):
            return ["- Contexto indisponivel."]
        lines = [_clean_sentence(item) for item in _as_text_list(context_summary.get("summary_lines"), limit=2)]
        lines = [line for line in lines if line]
        return [f"- {line}" for line in lines] or ["- Contexto indisponivel."]

    def _alternatives(self, alternatives: Any) -> list[str]:
        output = []
        for item in _as_dict_list(alternatives)[:2]:
            selection = str(item.get("selection") or "alternativa")
            market = str(item.get("market") or "mercado")
            reason = _clean_sentence(item.get("reason"))
            label = _short_market_label(selection, market)
            output.append(f"- {label}" + (f": {reason}" if reason else ""))
        return output or ["- Sem alternativa forte; melhor esperar mercado ou live."]

    def _avoid_line(self, avoid_markets: Any) -> str | None:
        avoid = _as_dict_list(avoid_markets)
        if not avoid:
            return None
        item = avoid[0]
        market = _clean_sentence(item.get("market"))
        reason = _clean_sentence(item.get("reason"))
        if not market:
            return None
        return market + (f" ({reason})" if reason else "")

    def _warning_line(self, warnings: Any, context_summary: Any) -> str | None:
        context_text = " ".join(_as_text_list((context_summary or {}).get("summary_lines") if isinstance(context_summary, dict) else None))
        cleaned = []
        for warning in _as_text_list(warnings, limit=4):
            text = _clean_sentence(warning)
            if not text or _is_redundant_warning(text, context_text):
                continue
            if _mentions_missing_odds(text):
                continue
            cleaned.append(text)
        if not cleaned:
            return None
        return "; ".join(_unique(cleaned[:2])) + "."

    def _odds_observation(self, main: dict[str, Any], advice: dict[str, Any]) -> str | None:
        value = main.get("value")
        if isinstance(value, dict):
            classification = value.get("classification")
            odd = _optional_float(value.get("odd"))
            fair = _optional_float(value.get("fair_odd") or main.get("fair_odd"))
            if odd is not None and fair is not None and classification:
                return f"odd {odd:.2f}, justa perto de {fair:.2f}; leitura {classification}."
            if classification:
                return f"leitura {classification}."

        note = _clean_sentence(main.get("odds_note"))
        error = _clean_sentence(advice.get("odds_error"))
        if note:
            return _short_odds_note(note, main)
        if error:
            return _short_odds_note(error, main)
        if _has_missing_odds_warning(advice.get("warnings")):
            return "sem linha equivalente para confirmar value nessa entrada."
        return None

    def _verdict(self, advice: dict[str, Any], main: dict[str, Any]) -> str:
        if _is_avoid(main):
            return _compact_summary(advice.get("final_verdict") or "melhor nao forcar entrada antes do jogo.")
        verdict = _clean_sentence(advice.get("final_verdict"))
        if verdict:
            return _compact_summary(verdict)
        return "shortlist boa, entrada so com linha e odd justas."


def _stake_phrase(main: dict[str, Any]) -> str:
    confidence = _normalize_label(main.get("confidence") or "baixa")
    risk = _normalize_label(main.get("risk_level") or "medio")
    if _is_avoid(main):
        return "Eu ficaria fora antes do jogo."
    if confidence == "alta" and risk == "baixo" and _positive_value(main.get("value")):
        return "Da para usar stake normal se a odd ainda estiver justa."
    if confidence in {"media", "alta"} and risk != "alto":
        return "Aqui eu reduziria stake ate confirmar time e odds."
    return "Trata como shortlist, nao como entrada automatica."


def _price_phrase(main: dict[str, Any]) -> str | None:
    value = main.get("value")
    if isinstance(value, dict):
        classification = value.get("classification")
        odd = _optional_float(value.get("odd"))
        fair = _optional_float(value.get("fair_odd") or main.get("fair_odd"))
        if odd is not None and fair is not None and classification:
            return f"Preco: odd {odd:.2f}, justa {fair:.2f}, {classification}."
        if classification:
            return f"Preco: {classification}."
    fair_odd = _optional_float(main.get("fair_odd"))
    if fair_odd is not None:
        return f"Minha justa fica perto de {fair_odd:.2f}."
    return None


def _short_market_label(selection: str, market: str) -> str:
    if market and market.lower() not in selection.lower():
        return f"{selection} ({market})"
    return selection


def _compact_summary(value: Any, max_chars: int = 190) -> str:
    text = _clean_sentence(value)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;")
    return f"{cut}."


def _clean_sentence(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _short_odds_note(text: str, main: dict[str, Any]) -> str:
    normalized = _normalize_label(text)
    market = _normalize_label(main.get("market"))
    if "prop" in market or "prop" in normalized:
        return "sem linha equivalente para props; nao da para confirmar value."
    if "amostras:" in normalized or "odds nao encontradas" in normalized or "odds nao encontrada" in normalized:
        return "encontrei evento parecido, mas sem mercado equivalente para essa entrada."
    if "linha equivalente" in normalized:
        return "sem linha equivalente para confirmar value nessa entrada."
    return _compact_summary(text, max_chars=130)


def _positive_value(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return value.get("classification") in {"value forte", "value moderado", "value leve"}


def _is_avoid(main: dict[str, Any]) -> bool:
    return _normalize_label(main.get("selection")) == "evitar" or "sem entrada" in _normalize_label(main.get("market"))


def _mentions_missing_odds(text: str) -> bool:
    normalized = _normalize_label(text)
    return "sem odds" in normalized or "confirmar value" in normalized or "linha equivalente" in normalized


def _has_missing_odds_warning(warnings: Any) -> bool:
    return any(_mentions_missing_odds(str(item)) for item in _as_text_list(warnings))


def _is_redundant_warning(warning: str, context_text: str) -> bool:
    normalized_warning = _normalize_label(warning)
    normalized_context = _normalize_label(context_text)
    if not normalized_context:
        return False
    return normalized_warning in normalized_context


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _as_text_list(value: Any, limit: int = 5) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple):
        return [str(item) for item in value[:limit] if item]
    return [str(value)]


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _unique(items: list[str]) -> list[str]:
    unique = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
