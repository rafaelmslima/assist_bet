from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.integrations.openai_client import OpenAIClient
from app.schemas.football_ai import FootballAIAnalysis


logger = logging.getLogger(__name__)


class FootballAIAnalysisService:
    """Delegates the final football match reading to the AI."""

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
        fallback = self._fallback_analysis(dossier)
        return {
            "advisor_text": _format_analysis(fallback),
            "mode": "football_ai_fallback",
            "dossier": dossier,
            "analysis": fallback.model_dump(),
        }

    def _fallback_analysis(self, dossier: dict[str, Any]) -> FootballAIAnalysis:
        fixture = dossier.get("fixture") or {}
        home = fixture.get("home_team") or "Mandante"
        away = fixture.get("away_team") or "Visitante"
        teams = dossier.get("teams") or {}
        home_team = teams.get("home") or {}
        away_team = teams.get("away") or {}
        context = dossier.get("competitive_context") or {}
        quality = dossier.get("data_quality") or {}
        notes = [str(item) for item in (quality.get("notes") or []) if str(item).strip()]
        script = _build_local_script(home, away, home_team, away_team)
        ideas = _build_local_betting_ideas(home, away, home_team, away_team, dossier.get("corners_context") or {})
        risks = _unique((context.get("context_alerts") or []) + notes[:3])
        if not risks:
            risks = ["confirmar escalacoes e desfalques antes de transformar a leitura em aposta"]

        return FootballAIAnalysis.model_validate(
            {
                "fixture_label": f"{home} x {away}",
                "general_idea": _local_general_idea(home, away, home_team, away_team),
                "expected_script": script,
                "tactical_matchups": _build_local_matchups(home, away, home_team, away_team),
                "motivation_context": _join_context_lines(context.get("summary_lines")) or "contexto competitivo parcial ou indisponivel.",
                "recent_form_read": _recent_form_read(home, away, home_team, away_team),
                "key_risks": risks[:5],
                "betting_ideas": ideas,
                "avoid": [
                    {
                        "market": "vencedor seco",
                        "reason": "sem preco e sem escalacoes confirmadas, o risco de leitura por resultado fica maior.",
                    }
                ],
                "confidence": {
                    "level": "vermelha" if quality.get("level") == "fraco" else "amarela",
                    "reason": notes[0] if notes else "leitura baseada nos dados disponiveis, ainda dependente de confirmacoes pre-jogo.",
                },
                "checklist_before_bet": [
                    "confirmar escalacoes oficiais",
                    "rever desfalques de ultima hora",
                    "comparar se o mercado escolhido ainda faz sentido perto do inicio",
                ],
                "data_quality_notes": notes or ["fallback local usado porque a IA nao respondeu com JSON valido"],
            }
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
    lines = [
        analysis.fixture_label,
        "",
        "Ideia geral:",
        analysis.general_idea,
        "",
        "Como deve ocorrer:",
        f"- Inicio: {analysis.expected_script.start}",
        f"- Desenvolvimento: {analysis.expected_script.middle}",
        f"- Se sair gol cedo: {analysis.expected_script.if_early_goal}",
        f"- Se chegar empatado no intervalo: {analysis.expected_script.if_level_at_halftime}",
        "",
        "Pontos-chave:",
    ]
    lines.extend(_matchup_lines(analysis.tactical_matchups))
    if analysis.motivation_context:
        lines.append(f"- Contexto/motivacao: {analysis.motivation_context}")
    if analysis.recent_form_read:
        lines.append(f"- Forma recente: {analysis.recent_form_read}")
    lines.extend(f"- Risco: {risk}" for risk in analysis.key_risks[:4])

    lines.extend(["", "Ideias de apostas:"])
    lines.extend(_betting_idea_lines(analysis.betting_ideas))
    lines.extend(["", "Evitaria:"])
    lines.extend(_avoid_lines(analysis.avoid))
    lines.extend(
        [
            "",
            "Confianca:",
            f"{analysis.confidence.level} - {analysis.confidence.reason}",
            "",
            "Antes de apostar:",
        ]
    )
    lines.extend(f"- {item}" for item in (analysis.checklist_before_bet or ["confirmar dados finais do jogo"])[:4])

    if analysis.data_quality_notes:
        lines.extend(["", "Limitacoes dos dados:"])
        lines.extend(f"- {item}" for item in analysis.data_quality_notes[:4])
    return "\n".join(line for line in lines if line is not None)


def _matchup_lines(matchups: list[Any]) -> list[str]:
    if not matchups:
        return ["- Sem matchup forte o bastante nos dados disponiveis."]
    return [f"- {item.title}: {item.reading}" for item in matchups[:4]]


def _betting_idea_lines(ideas: list[Any]) -> list[str]:
    if not ideas:
        return ["1. Sem ideia forte - melhor tratar como jogo de observacao."]
    rows = []
    for index, item in enumerate(ideas[:4], start=1):
        rows.append(f"{index}. {item.market} - {item.idea} | confianca {item.confidence}: {item.reason}")
    return rows


def _avoid_lines(avoid: list[Any]) -> list[str]:
    if not avoid:
        return ["- Forcar mercado sem confirmacao do roteiro."]
    return [f"- {item.market}: {item.reason}" for item in avoid[:3]]


def _local_general_idea(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any]) -> str:
    home_goal = _avg_known(home_team.get("goals", {}).get("home_avg_scored"), away_team.get("goals", {}).get("away_avg_conceded"))
    away_goal = _avg_known(away_team.get("goals", {}).get("away_avg_scored"), home_team.get("goals", {}).get("home_avg_conceded"))
    if home_goal is not None and away_goal is not None:
        if home_goal >= away_goal + 0.35:
            return f"O jogo tende a passar mais pelo {home}, com o {away} precisando sobreviver sem se expor demais."
        if away_goal >= home_goal + 0.35:
            return f"O {away} tem sinais para incomodar fora, entao o jogo nao parece simples para o mandante."
        return "Os dados apontam equilibrio razoavel, com leitura mais segura em roteiro de jogo do que em vencedor."
    return "Ha dados parciais para montar uma leitura, mas nao o bastante para cravar um roteiro forte."


def _build_local_script(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any]) -> dict[str, str]:
    home_goal = _avg_known(home_team.get("goals", {}).get("home_avg_scored"), away_team.get("goals", {}).get("away_avg_conceded"))
    away_goal = _avg_known(away_team.get("goals", {}).get("away_avg_scored"), home_team.get("goals", {}).get("home_avg_conceded"))
    total = _sum_known(home_goal, away_goal)
    tempo = "controlado" if total is not None and total < 2.2 else "mais aberto" if total is not None and total >= 2.6 else "de ritmo moderado"
    return {
        "start": f"Tendencia de inicio {tempo}, com o {home} tentando organizar a primeira fase do jogo.",
        "middle": "O desenvolvimento deve depender de quem conseguir transformar posse/territorio em chances claras.",
        "if_early_goal": "Um gol cedo deve abrir mais espaco para transicoes e aumentar a utilidade de mercados de gols.",
        "if_level_at_halftime": "Se chegar empatado no intervalo, a leitura pede cautela e mais peso para ajustes e banco.",
    }


def _build_local_matchups(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any]) -> list[dict[str, str]]:
    home_goal = _avg_known(home_team.get("goals", {}).get("home_avg_scored"), away_team.get("goals", {}).get("away_avg_conceded"))
    away_goal = _avg_known(away_team.get("goals", {}).get("away_avg_scored"), home_team.get("goals", {}).get("home_avg_conceded"))
    rows = []
    if home_goal is not None:
        rows.append({"title": f"Ataque do {home}", "reading": f"sinal combinado de gols em casa/defesa visitante perto de {home_goal:.2f}."})
    if away_goal is not None:
        rows.append({"title": f"Resposta do {away}", "reading": f"sinal combinado de producao visitante perto de {away_goal:.2f}."})
    return rows or [{"title": "Matchup principal", "reading": "amostra estatistica incompleta para destacar vantagem clara."}]


def _build_local_betting_ideas(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any], corners: dict[str, Any]) -> list[dict[str, str]]:
    home_goal = _avg_known(home_team.get("goals", {}).get("home_avg_scored"), away_team.get("goals", {}).get("away_avg_conceded"))
    away_goal = _avg_known(away_team.get("goals", {}).get("away_avg_scored"), home_team.get("goals", {}).get("home_avg_conceded"))
    total = _sum_known(home_goal, away_goal)
    ideas: list[dict[str, str]] = []
    if total is not None and total >= 2.2:
        ideas.append({"market": "gols", "idea": "over 1.5 gols", "confidence": "media", "reason": "os sinais combinados de producao ofensiva sustentam ao menos dois gols."})
    if home_goal is not None and home_goal >= 1.25:
        ideas.append({"market": "gol do mandante", "idea": f"{home} marcar", "confidence": "media", "reason": "o recorte casa/fora favorece participacao ofensiva do mandante."})
    if away_goal is not None and away_goal >= 1.05:
        ideas.append({"market": "gol do visitante", "idea": f"{away} marcar", "confidence": "baixa", "reason": "ha sinal para resposta visitante, mas depende do roteiro e da escalação."})
    corner_avg = _to_float(corners.get("combined_team_corners_avg"))
    if corner_avg is not None and corner_avg >= 8:
        ideas.append({"market": "escanteios", "idea": "olhar linha de escanteios", "confidence": "baixa", "reason": "amostra recente sugere volume lateral, mas precisa confirmar linha e estilo."})
    return ideas[:4] or [{"market": "sem mercado claro", "idea": "jogo para observacao", "confidence": "baixa", "reason": "os dados nao sustentam uma ideia qualitativa forte."}]


def _recent_form_read(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any]) -> str:
    home_form = home_team.get("form", {}).get("last_5") or "indisponivel"
    away_form = away_team.get("form", {}).get("last_5") or "indisponivel"
    return f"{home}: {home_form}; {away}: {away_form}. Use forma como contexto, nao como gatilho isolado."


def _join_context_lines(lines: Any) -> str:
    if not isinstance(lines, list):
        return ""
    cleaned = [str(line).strip() for line in lines if str(line).strip()]
    return " ".join(cleaned[:3])


def _avg_known(*values: Any) -> float | None:
    known = [_to_float(value) for value in values]
    nums = [value for value in known if value is not None]
    return round(sum(nums) / len(nums), 2) if nums else None


def _sum_known(*values: Any) -> float | None:
    known = [_to_float(value) for value in values]
    nums = [value for value in known if value is not None]
    return round(sum(nums), 2) if len(nums) >= 2 else None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique(items: list[Any]) -> list[str]:
    rows: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in rows:
            rows.append(text)
    return rows
