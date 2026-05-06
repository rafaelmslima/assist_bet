from __future__ import annotations

import unicodedata
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"


class FootballResponseService:
    """Builds the professional football advisory response sent to Telegram."""

    def format_advice(self, advice: dict[str, Any]) -> str:
        fixture = advice.get("fixture") or {}
        main = advice.get("main_recommendation") or {}
        home = fixture.get("home_team") or fixture.get("home_team_name") or "Mandante"
        away = fixture.get("away_team") or fixture.get("away_team_name") or "Visitante"

        lines = [
            f"{home} x {away}",
            "",
            self._decision_line(main),
            self._confidence_line(main),
            self._stake_line(main, advice),
            "",
            "Motivo:",
            self._main_reason(main, advice),
            "",
            "Contexto:",
            *self._context_lines(advice.get("context_summary")),
            "",
            "Preco e value:",
            *self._value_lines(main),
        ]

        alternatives = self._alternatives(advice.get("alternative_recommendations"))
        if alternatives:
            lines.extend(["", "Alternativas:", *alternatives])

        avoid = self._avoid_line(advice.get("avoid_markets"))
        lines.extend(["", "Evitaria:", avoid])

        warnings = self._warning_lines(advice.get("warnings"))
        if warnings:
            lines.extend(["", "Antes de entrar:", *warnings])

        lines.extend(
            [
                "",
                f"Veredito: {advice.get('final_verdict') or 'Sem entrada automatica. Use a leitura como apoio e confirme preco/contexto.'}",
            ]
        )
        return "\n".join(str(line) for line in lines if line is not None)

    def _decision_line(self, main: dict[str, Any]) -> str:
        market = main.get("market") or "mercado"
        selection = main.get("selection") or "evitar"
        return f"Melhor aposta: {selection} ({market})"

    def _confidence_line(self, main: dict[str, Any]) -> str:
        confidence = _normalize_label(main.get("confidence") or "baixa")
        risk = _normalize_label(main.get("risk_level") or "medio")
        return f"Confianca: {confidence} | Risco: {risk}"

    def _stake_line(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        confidence = _normalize_label(main.get("confidence") or "baixa")
        risk = _normalize_label(main.get("risk_level") or "medio")
        value = main.get("value")
        if confidence == "alta" and risk == "baixo" and _positive_value(value):
            return "Gestao sugerida: entrada normal, se a odd real ainda estiver justa."
        if confidence in {"media", "alta"} and risk != "alto":
            return "Gestao sugerida: stake reduzida ate confirmar odds e escalacoes."
        if _is_avoid(main):
            return "Gestao sugerida: sem entrada pre-jogo."
        return "Gestao sugerida: apenas shortlist; nao transformar em aposta sem confirmacao."

    def _main_reason(self, main: dict[str, Any], advice: dict[str, Any]) -> str:
        summary = main.get("summary")
        if summary:
            return str(summary)
        factors = _as_text_list(advice.get("key_factors"), limit=2)
        if factors:
            return " ".join(factors)
        return "Os dados atuais nao sustentam vantagem clara o bastante."

    def _context_lines(self, context_summary: Any) -> list[str]:
        if not isinstance(context_summary, dict):
            return ["- Contexto indisponivel."]
        lines = _as_text_list(context_summary.get("summary_lines"), limit=3)
        alerts = _as_text_list(context_summary.get("context_alerts"), limit=2)
        output = [f"- {item}" for item in lines if item]
        output.extend(f"- Alerta: {item}" for item in alerts if item and item not in lines)
        return output or ["- Contexto indisponivel."]

    def _value_lines(self, main: dict[str, Any]) -> list[str]:
        value = main.get("value")
        estimated = _optional_float(main.get("estimated_probability"))
        fair_odd = _optional_float(main.get("fair_odd"))
        lines: list[str] = []

        if isinstance(value, dict):
            odd = _optional_float(value.get("odd"))
            implied = _optional_float(value.get("implied_probability"))
            edge = _optional_float(value.get("edge"))
            classification = value.get("classification") or "sem value claro"
            if odd is not None:
                lines.append(f"- Odd atual: {odd:.2f}")
            if implied is not None:
                lines.append(f"- Probabilidade implicita: {_percent(implied)}")
            if estimated is not None:
                lines.append(f"- Minha estimativa: {_percent(estimated)}")
            if fair_odd is not None:
                lines.append(f"- Odd justa estimada: {fair_odd:.2f}")
            if edge is not None:
                lines.append(f"- Edge: {_percent(edge)}")
            lines.append(f"- Leitura: {classification}.")
            return lines

        if estimated is not None:
            lines.append(f"- Minha estimativa: {_percent(estimated)}")
        if fair_odd is not None:
            lines.append(f"- Odd justa estimada: {fair_odd:.2f}")
        if main.get("odds_available"):
            lines.append("- Odds encontradas, mas sem linha equivalente exata para confirmar value.")
            note = main.get("odds_note")
            if note:
                lines.append(f"- {note}")
            for item in _as_text_list(main.get("odds_summary"), limit=3):
                lines.append(f"- Disponivel: {item}")
            return lines

        min_odd = _optional_float(main.get("min_acceptable_odd"))
        if min_odd is not None:
            lines.append(f"- Sem odds equivalentes. Eu so consideraria acima de {min_odd:.2f}.")
        else:
            lines.append("- Sem odds equivalentes. Nao classificar como value.")
        return lines

    def _alternatives(self, alternatives: Any) -> list[str]:
        output = []
        for item in _as_dict_list(alternatives)[:2]:
            selection = item.get("selection") or "alternativa"
            market = item.get("market") or "mercado"
            reason = item.get("reason")
            suffix = f" - {reason}" if reason else ""
            output.append(f"- {selection} ({market}){suffix}")
        return output

    def _avoid_line(self, avoid_markets: Any) -> str:
        avoid = _as_dict_list(avoid_markets)
        if not avoid:
            return "- Entrada forte sem confirmar odds, escalacoes e desfalques."
        item = avoid[0]
        market = item.get("market") or "mercado"
        reason = item.get("reason")
        return f"- {market}" + (f" - {reason}" if reason else "")

    def _warning_lines(self, warnings: Any) -> list[str]:
        return [f"- {item}" for item in _as_text_list(warnings, limit=3)]


def _positive_value(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return value.get("classification") in {"value forte", "value moderado", "value leve"}


def _is_avoid(main: dict[str, Any]) -> bool:
    return _normalize_label(main.get("selection")) == "evitar" or "sem entrada" in _normalize_label(main.get("market"))


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


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "0.00%"
