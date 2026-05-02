from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"


@dataclass(frozen=True)
class PlayerMarketCandidate:
    player: dict[str, Any]
    market: str
    selection: str
    stat_label: str
    stat_value: float
    score: float
    risk_points: float
    reasons: list[str]
    warnings: list[str]


class PlayerAdvisorService:
    """Turns football player stats into betting-oriented prop shortlists."""

    def advise_fixture_players(self, context: Any, limit: int = 5) -> dict[str, Any]:
        players = list(getattr(context, "players", []) or [])
        fixture = getattr(context, "fixture", {}) or {}
        injuries = list(getattr(context, "injuries", []) or [])
        data_quality = list(getattr(context, "data_quality", []) or [])
        lineups = getattr(context, "lineups", {}) or {}

        candidates: list[PlayerMarketCandidate] = []
        for player in players:
            if player.get("injured"):
                continue
            candidates.extend(_player_candidates(player))

        candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
        if not candidates:
            return {
                "fixture": fixture,
                "best": None,
                "recommendations": [],
                "injuries": injuries,
                "data_quality": data_quality,
                "lineups_confirmed": bool(lineups.get("confirmed")),
                "final_verdict": (
                    "Eu nao vejo prop confiavel com os dados disponiveis. Melhor esperar escalacao, linhas e dados individuais."
                ),
            }

        selected = _dedupe_players(candidates)[:limit]
        return {
            "fixture": fixture,
            "best": _candidate_to_dict(selected[0]),
            "recommendations": [_candidate_to_dict(item) for item in selected],
            "injuries": injuries,
            "data_quality": data_quality,
            "lineups_confirmed": bool(lineups.get("confirmed")),
            "final_verdict": _fixture_player_verdict(selected[0], bool(lineups.get("confirmed"))),
        }

    def format_injuries(self, context: Any) -> str:
        fixture = getattr(context, "fixture", {}) or {}
        injuries = list(getattr(context, "injuries", []) or [])
        data_quality = list(getattr(context, "data_quality", []) or [])
        home = fixture.get("home_team") or "Mandante"
        away = fixture.get("away_team") or "Visitante"

        lines = [f"Desfalques - {home} x {away}", ""]
        if not injuries:
            lines.append("Nao encontrei desfalques confirmados na API para este jogo.")
            if data_quality:
                lines.extend(["", "Observacoes:"])
                lines.extend(f"- {item}" for item in data_quality[:4])
            lines.extend(["", "Veredito: sem desfalques confiaveis, eu nao ajustaria a leitura apenas por esse fator."])
            return "\n".join(lines)

        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in injuries:
            grouped.setdefault(str(item.get("team_name") or "Time"), []).append(item)

        for team_name, items in grouped.items():
            lines.append(team_name)
            for item in items[:8]:
                reason = item.get("reason") or item.get("type") or "motivo nao informado"
                lines.append(f"- {item.get('player_name')}: {reason}")
            lines.append("")

        lines.append("Veredito: desfalques importantes podem mudar mercado de gols, vencedor e props. Confirme antes de entrar.")
        return "\n".join(lines).strip()


def format_fixture_player_advice(advice: dict[str, Any]) -> str:
    fixture = advice.get("fixture") or {}
    home = fixture.get("home_team") or "Mandante"
    away = fixture.get("away_team") or "Visitante"

    lines = [f"Jogadores interessantes - {home} x {away}", ""]
    best = advice.get("best")
    if not best:
        lines.extend(
            [
                "Eu nao encontrei uma prop confiavel com os dados disponiveis.",
                "",
                "Por que:",
            ]
        )
        lines.extend(f"- {item}" for item in (advice.get("data_quality") or ["dados individuais indisponiveis"])[:4])
        lines.extend(["", f"Veredito: {advice.get('final_verdict')}"])
        return "\n".join(lines)

    lines.extend(
        [
            "Melhor leitura:",
            f"{best.get('player')} - {best.get('selection')}",
            f"Risco: {best.get('risk_level')}",
            "",
            "Por que faz sentido:",
        ]
    )
    lines.extend(f"- {item}" for item in (best.get("reasons") or [])[:3])

    warnings = best.get("warnings") or []
    if warnings:
        lines.extend(["", "O que confirmar:"])
        lines.extend(f"- {item}" for item in warnings[:3])

    recommendations = advice.get("recommendations") or []
    if len(recommendations) > 1:
        lines.extend(["", "Outras leituras:"])
        for item in recommendations[1:5]:
            lines.append(f"- {item.get('player')}: {item.get('selection')} ({item.get('risk_level')})")

    quality = advice.get("data_quality") or []
    if quality:
        lines.extend(["", "Qualidade dos dados:"])
        lines.extend(f"- {item}" for item in quality[:3])

    lines.extend(
        [
            "",
            "Veredito:",
            str(advice.get("final_verdict") or "Eu usaria como shortlist, nao como entrada automatica."),
            "",
            "Use como apoio de analise, nao como garantia. Aposte com gestao de banca.",
        ]
    )
    return "\n".join(lines)


def _player_candidates(player: dict[str, Any]) -> list[PlayerMarketCandidate]:
    candidates = []
    for key, label, min_avg, weight in (
        ("shots", "finalizacoes", 1.4, 1.0),
        ("shots_on_target", "finalizacoes no alvo", 0.5, 1.2),
        ("goals", "gol", 0.25, 1.1),
        ("assists", "assistencia", 0.18, 0.9),
        ("cards", "cartao", 0.22, 0.8),
    ):
        value = _avg_per_appearance(player, key)
        if value is None or value <= 0:
            continue

        score = value * weight
        risk = 0.5
        reasons = [f"media de {value:.2f} em {label} por jogo na amostra disponivel."]
        warnings = []
        minutes = _to_float(player.get("minutes"))
        appearances = _to_float(player.get("appearances"))
        position = str(player.get("position") or "").upper()

        if value >= min_avg:
            score += 1.0
            reasons.append("volume acima do minimo que eu considero interessante para shortlist.")
        else:
            risk += 0.8
            warnings.append("linha precisa estar baixa, porque o volume medio nao e alto.")

        if appearances is not None and appearances < 5:
            risk += 1.0
            warnings.append("amostra pequena de jogos.")
        if minutes is not None and appearances and minutes / appearances < 55:
            risk += 1.0
            warnings.append("minutagem media baixa ou instavel.")
        if player.get("starter") is False and player.get("substitute"):
            risk += 1.0
            warnings.append("aparece como reserva/substituto.")
        if player.get("starter") is None:
            warnings.append("titularidade ainda nao confirmada.")
        elif player.get("starter"):
            score += 0.7
            reasons.append("titularidade aparece confirmada na API.")

        if key in {"shots", "shots_on_target", "goals"} and position.startswith("D"):
            risk += 0.6
            warnings.append("posicao tende a reduzir volume ofensivo.")
        if key == "cards" and position.startswith(("D", "M")):
            score += 0.4
            reasons.append("funcao/posicao costuma estar mais exposta a duelos.")

        if score < 1.2:
            continue

        candidates.append(
            PlayerMarketCandidate(
                player=player,
                market=label,
                selection=_selection_text(label, value),
                stat_label=label,
                stat_value=value,
                score=score - risk * 0.25,
                risk_points=risk,
                reasons=reasons,
                warnings=warnings,
            )
        )
    return candidates


def _candidate_to_dict(candidate: PlayerMarketCandidate) -> dict[str, Any]:
    player = candidate.player
    return {
        "player": player.get("player_name"),
        "team": player.get("team_name"),
        "position": player.get("position"),
        "market": candidate.market,
        "selection": candidate.selection,
        "stat_value": round(candidate.stat_value, 2),
        "confidence": _confidence(candidate.score, candidate.risk_points),
        "risk_level": _risk_level(candidate.risk_points),
        "reasons": candidate.reasons,
        "warnings": candidate.warnings,
    }


def _dedupe_players(candidates: list[PlayerMarketCandidate]) -> list[PlayerMarketCandidate]:
    selected: list[PlayerMarketCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.player.get("player_id") or candidate.player.get("player_name"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
    return selected


def _fixture_player_verdict(candidate: PlayerMarketCandidate, lineups_confirmed: bool) -> str:
    player_name = candidate.player.get("player_name") or "esse jogador"
    if lineups_confirmed:
        return f"Eu olharia primeiro para {player_name} em {candidate.market}, mas ainda compararia com a linha e odd oferecidas."
    return f"Eu colocaria {player_name} em shortlist para {candidate.market}, mas so consideraria entrada com titularidade confirmada."


def _selection_text(label: str, value: float) -> str:
    if label == "gol":
        return "marcar gol ou finalizar, dependendo da odd"
    if label == "assistencia":
        return "assistencia ou passes-chave, se a casa oferecer linha justa"
    if label == "cartao":
        return "cartao, apenas se o arbitro/contexto ajudarem"
    return f"over em {label}, se a linha estiver perto de {max(0.5, value - 0.4):.1f}"


def _avg_per_appearance(player: dict[str, Any], key: str) -> float | None:
    value = _to_float(player.get(key))
    if value is None:
        return None
    if player.get("source") == "fixture":
        return value
    appearances = _to_float(player.get("appearances"))
    if appearances is None or appearances <= 0:
        return value
    return value / appearances


def _confidence(score: float, risk: float) -> str:
    if risk >= 2.0 or score < 1.4:
        return "baixa"
    if score >= 2.5 and risk < 1.2:
        return "alta"
    return "media"


def _risk_level(risk: float) -> str:
    if risk >= 2.0:
        return "alto"
    if risk >= 1.0:
        return "medio"
    return "baixo"


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None
