from __future__ import annotations

from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"


class ValueService:
    """Calculates initial value betting indicators."""

    def implied_probability(self, odd: float) -> float:
        if odd <= 1:
            raise ValueError("Odd decimal deve ser maior que 1.")
        return 1 / odd

    def decimal_odd_from_probability(self, probability: float) -> float:
        if probability <= 0 or probability > 1:
            raise ValueError("Probabilidade deve estar entre 0 e 1.")
        return 1 / probability

    def estimate_team_probability(self, analysis_data: dict[str, Any]) -> float:
        """Estimate a probability from available qualitative analysis signals."""
        probability = 0.5

        probability += _score_label(analysis_data.get("forma_recente"), positive=0.06, negative=-0.06)
        probability += _score_label(analysis_data.get("força_ofensiva"), positive=0.05, negative=-0.05)
        probability += _score_label(analysis_data.get("força_defensiva"), positive=0.04, negative=-0.04)
        probability += _score_home_away(analysis_data.get("desempenho_casa"), analysis_data.get("desempenho_fora"))
        probability += _score_context(analysis_data.get("contexto") or analysis_data.get("context"))
        probability += _score_rotation(analysis_data.get("risco_de_rotação") or analysis_data.get("rotation_risk"))
        probability += _score_injuries(analysis_data.get("lesões") or analysis_data.get("injuries") or analysis_data.get("alerts"))
        probability += _score_matchup(analysis_data.get("matchup") or analysis_data.get("leitura_de_matchup"))

        return _clamp(probability, minimum=0.01, maximum=0.99)

    def calculate_value(self, estimated_probability: float, market_odd: float) -> dict[str, Any]:
        if estimated_probability <= 0 or estimated_probability > 1:
            raise ValueError("Probabilidade estimada deve estar entre 0 e 1.")

        market_implied_probability = self.implied_probability(market_odd)
        edge = estimated_probability - market_implied_probability
        confidence_level = _confidence_level(edge)

        return {
            "implied_probability": round(market_implied_probability, 4),
            "estimated_probability": round(estimated_probability, 4),
            "edge": round(edge, 4),
            "has_value": edge > 0.02,
            "confidence_level": confidence_level,
        }

    def format_value_analysis(self, value_data: dict[str, Any]) -> str:
        implied = value_data.get("implied_probability")
        estimated = value_data.get("estimated_probability")
        edge = value_data.get("edge")
        confidence = value_data.get("confidence_level", INSUFFICIENT_DATA)
        has_value = value_data.get("has_value")

        if implied is None or estimated is None or edge is None:
            return "Dados insuficientes para calcular value betting."

        status = "Value positivo" if has_value else "Sem value claro"
        return (
            f"{status}\n"
            f"Probabilidade implícita da odd: {_as_percent(implied)}\n"
            f"Probabilidade estimada: {_as_percent(estimated)}\n"
            f"Edge estimado: {_as_percent(edge)}\n"
            f"Confiança: {confidence}\n\n"
            "A probabilidade é uma estimativa baseada nos dados disponíveis, não uma garantia de resultado."
        )

    def calculate_expected_value(self, probability: float, odds: float) -> float:
        """Backward-compatible expected value helper."""
        return (probability * odds) - 1

    def has_value(self, probability: float, odds: float, minimum_edge: float = 0.01) -> bool:
        """Backward-compatible boolean helper."""
        return self.calculate_expected_value(probability, odds) >= minimum_edge


def _score_label(value: Any, *, positive: float, negative: float) -> float:
    label = _normalize_text(value)
    if label in {"forte", "alta", "favorável", "favoravel", "positivo"}:
        return positive
    if label in {"fraca", "baixa", "desfavorável", "desfavoravel", "negativo"}:
        return negative
    return 0


def _score_home_away(home_performance: Any, away_performance: Any) -> float:
    text = f"{_normalize_text(home_performance)} {_normalize_text(away_performance)}"
    if INSUFFICIENT_DATA in text or not text.strip():
        return 0
    if "vantagem" in text or "marca" in text:
        return 0.03
    if "fora" in text and "fraco" in text:
        return 0.02
    return 0


def _score_context(context: Any) -> float:
    if isinstance(context, dict):
        motivation = context.get("motivation_level")
        fatigue = context.get("fatigue_risk")
        score = 0.0
        if motivation == "alta":
            score += 0.04
        elif motivation == "baixa":
            score -= 0.04
        if fatigue == "alto":
            score -= 0.04
        elif fatigue == "médio":
            score -= 0.02
        return score

    text = _normalize_text(context)
    if "motivação alta" in text or "motivacao alta" in text:
        return 0.04
    if "fadiga alta" in text or "rotação alta" in text or "rotacao alta" in text:
        return -0.04
    return 0


def _score_rotation(rotation_risk: Any) -> float:
    risk = _normalize_text(rotation_risk)
    if risk == "alto":
        return -0.05
    if risk in {"médio", "medio"}:
        return -0.025
    return 0


def _score_injuries(injuries: Any) -> float:
    if not injuries:
        return 0
    if isinstance(injuries, list):
        joined = " ".join(_normalize_text(item) for item in injuries)
    else:
        joined = _normalize_text(injuries)

    if "desfalque" in joined or "les" in joined or "suspens" in joined:
        return -0.04
    return 0


def _score_matchup(matchup: Any) -> float:
    text = _normalize_text(matchup)
    if not text or INSUFFICIENT_DATA in text:
        return 0
    if "favorável" in text or "favoravel" in text or "melhor fase" in text:
        return 0.05
    if "travado" in text or "desfavorável" in text or "desfavoravel" in text:
        return -0.03
    return 0


def _confidence_level(edge: float) -> str:
    if edge > 0.05:
        return "value positivo"
    if 0.02 <= edge <= 0.05:
        return "leve value"
    return "sem value"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _clamp(value: float, *, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _as_percent(value: float) -> str:
    return f"{value * 100:.2f}%"
