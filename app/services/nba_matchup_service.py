from __future__ import annotations

from typing import Any


class NbaMatchupService:
    """Simple NBA matchup context for props-first analysis."""

    def analyze_matchup(self, player: dict[str, Any], opponent_team: dict[str, Any]) -> dict[str, Any]:
        position = str(player.get("position") or "").upper()
        opponent_allowed = _to_float(opponent_team.get("points_against_avg"))
        game_total = _to_float(opponent_team.get("game_total_avg"))

        score = 0.0
        factors = []
        warnings = []

        if opponent_allowed is not None and opponent_allowed >= 115:
            score += 0.8
            factors.append("adversario vem permitindo pontuacao alta recentemente.")
        elif opponent_allowed is not None and opponent_allowed <= 108:
            score -= 0.6
            warnings.append("adversario tem recorte defensivo mais duro.")

        if game_total is not None and game_total >= 225:
            score += 0.6
            factors.append("jogos recentes do adversario apontam ambiente de pontuacao mais alto.")
        elif game_total is not None and game_total <= 215:
            score -= 0.4
            warnings.append("ritmo/total recente nao favorece linha esticada.")

        if position.startswith("G"):
            factors.append("posicao de guard tende a favorecer pontos, assistencias e bolas de 3.")
        elif "C" in position or position.startswith("F-C"):
            factors.append("perfil de big favorece rebotes e PRA quando a minutagem sustenta.")
        elif position.startswith("F"):
            factors.append("ala costuma ter leitura mais equilibrada entre pontos, rebotes e PRA.")

        return {"score": score, "factors": factors, "warnings": warnings}


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None
