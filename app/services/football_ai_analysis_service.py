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
                "data_quality_read": _local_data_quality_read(dossier),
                "team_profiles_read": _local_team_profiles_read(dossier),
                "market_assessments": _local_market_assessments(dossier),
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
    blocks = [
        analysis.fixture_label,
        _section("Leitura do jogo", _opening_paragraph(analysis)),
        _section("Qualidade dos dados", _data_quality_block(analysis)),
        _section("Raio-X dos times", _team_profiles_block(analysis)),
        _section("Roteiro provável", _script_paragraph(analysis)),
        _section("Fatores que pesam", _context_block(analysis)),
        _section("Scores de mercado", _market_scores_block(analysis)),
        _section("Ideias de mercado", _market_block(analysis)),
    ]
    confidence_note = _confidence_note(analysis)
    if confidence_note:
        blocks.append(_section("Confiança", confidence_note))
    return "\n\n".join(block for block in blocks if block)


def _section(title: str, body: str) -> str:
    if not body:
        return ""
    return f"{title}\n{body}"


def _opening_paragraph(analysis: FootballAIAnalysis) -> str:
    idea = _sentence(analysis.general_idea)
    return _capitalize_first(idea) or "Os dados ainda não deixam o jogo totalmente claro."


def _script_paragraph(analysis: FootballAIAnalysis) -> str:
    script = analysis.expected_script
    first = _sentence(script.start) or "O começo deve dar uma boa pista do ritmo real da partida."
    middle = _sentence(script.middle)
    early = _sentence(script.if_early_goal)
    level = _sentence(script.if_level_at_halftime)

    lines = [first]
    if middle:
        lines.append(middle)
    if early or level:
        lines.append("")
        if early:
            lines.append(f"Se o jogo abrir cedo: {early}")
        if level:
            lines.append(f"Se chegar empatado ao intervalo: {level}")
    return "\n".join(lines)


def _context_block(analysis: FootballAIAnalysis) -> str:
    matchup = _best_matchup_text(analysis)
    context = _sentence(analysis.motivation_context)
    form = _sentence(analysis.recent_form_read)
    risk = _first_text(analysis.key_risks)

    lines = []
    if matchup:
        lines.append(f"- Matchup: {matchup}")
    if context:
        lines.append(f"- Contexto: {context}")
    if form:
        lines.append(f"- Forma: {form}")
    if risk:
        lines.append(f"- Risco principal: {_sentence(risk)}")
    return "\n".join(lines) or "Os dados ainda não mostram um encaixe forte o bastante para exagerar na convicção."


def _data_quality_block(analysis: FootballAIAnalysis) -> str:
    read = _sentence(getattr(analysis, "data_quality_read", ""))
    if read:
        return read
    notes = [str(item) for item in analysis.data_quality_notes[:2] if str(item).strip()]
    if notes:
        return " ".join(_sentence(item) for item in notes)
    return ""


def _team_profiles_block(analysis: FootballAIAnalysis) -> str:
    lines = []
    for item in getattr(analysis, "team_profiles_read", [])[:3]:
        text = _sentence(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def _market_scores_block(analysis: FootballAIAnalysis) -> str:
    rows = []
    for item in getattr(analysis, "market_assessments", [])[:6]:
        market = _clean_text(getattr(item, "market", ""))
        score = getattr(item, "score", None)
        confidence = _clean_text(getattr(item, "confidence", ""))
        reading = _sentence(getattr(item, "reading", ""))
        risk = _sentence(getattr(item, "risk", ""))
        value = _sentence(getattr(item, "value_note", ""))
        if not market:
            continue
        line = f"- {market}: {score}/100"
        if confidence:
            line += f" ({confidence})"
        if reading:
            line += f". {reading}"
        if risk:
            line += f" Risco: {risk}"
        if value:
            line += f" {value}"
        rows.append(line)
    return "\n".join(rows)


def _market_block(analysis: FootballAIAnalysis) -> str:
    lines = _market_idea_lines(analysis)
    avoid = _avoid_text(analysis)
    if avoid:
        lines.append(f"- Evitaria: {_sentence(avoid)}")
    if not lines:
        lines.append("Eu trataria esse jogo mais como observação do que como entrada pré-jogo.")
    return "\n".join(lines)


def _confidence_note(analysis: FootballAIAnalysis) -> str:
    reason = _sentence(analysis.confidence.reason)
    checklist = _first_text(analysis.checklist_before_bet)
    if analysis.confidence.level == "verde" and not checklist:
        return ""
    confidence = f"{analysis.confidence.level.capitalize()}."
    if reason:
        confidence += f" {_capitalize_first(reason)}"
    if checklist:
        confidence += f" Antes de apostar, eu confirmaria {_strip_confirm_prefix(checklist)}."
    return confidence


def _best_matchup_text(analysis: FootballAIAnalysis) -> str:
    for item in analysis.tactical_matchups:
        title = _clean_text(item.title)
        reading = _sentence(item.reading)
        if title and reading and not _title_repeats_fixture(title, analysis.fixture_label):
            return f"{title}: {reading}"
        if reading:
            return reading
    return ""


def _market_idea_lines(analysis: FootballAIAnalysis) -> list[str]:
    if not analysis.betting_ideas:
        return []
    lines = []
    for item in analysis.betting_ideas[:3]:
        market = _clean_text(item.market)
        idea = _clean_text(item.idea) or market
        reason = _clean_text(item.reason)
        projection = _projection_text(item)
        label = market.capitalize() if market else "Mercado"
        if idea and projection:
            line = f"- {label}: {_sentence(idea)} {_sentence(projection)}"
        elif idea and reason:
            line = f"- {label}: {_sentence(idea)}"
        elif idea:
            line = f"- {label}: {_sentence(idea)}"
        else:
            continue
        if reason:
            line += f" {_sentence(reason)}"
        lines.append(line)
    return lines


def _projection_text(item: Any) -> str:
    projection = _clean_text(getattr(item, "projection", ""))
    projection_analysis = _clean_text(getattr(item, "projection_analysis", ""))
    if projection and projection_analysis:
        return f"Projeção: {projection}. {projection_analysis}"
    if projection:
        return f"Projeção: {projection}"
    if _is_quantitative_prop(getattr(item, "market", ""), getattr(item, "idea", "")):
        return "Sem número confiável nos dados atuais; eu não transformaria isso em prop antes de ter uma linha melhor"
    return ""


def _is_quantitative_prop(*values: Any) -> bool:
    text = " ".join(str(value or "").lower() for value in values)
    keywords = (
        "escanteio",
        "canto",
        "cantos",
        "cartao",
        "cartoes",
        "finalizacao",
        "finalizacoes",
        "chute",
        "chutes",
        "desarme",
        "desarmes",
        "prop",
    )
    return any(keyword in text for keyword in keywords)


def _avoid_text(analysis: FootballAIAnalysis) -> str:
    if not analysis.avoid:
        return ""
    item = analysis.avoid[0]
    market = _clean_text(item.market)
    reason = _clean_text(item.reason)
    if market and reason:
        return f"{market}, porque {_sentence(reason[0].lower() + reason[1:])}"
    return market


def _natural_join(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} ou {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} ou {cleaned[-1]}"


def _title_repeats_fixture(title: str, fixture_label: str) -> bool:
    normalized_title = _normalize_name(title)
    normalized_fixture = _normalize_name(fixture_label)
    return bool(normalized_title and normalized_fixture and normalized_title == normalized_fixture)


def _strip_confirm_prefix(value: str) -> str:
    text = _clean_text(value)
    lowered = text.lower()
    for prefix in ("confirmar ", "conferir ", "checar ", "verificar "):
        if lowered.startswith(prefix):
            return text[len(prefix):]
    return text


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().replace(" x ", " vs ").split())


def _first_text(items: list[str]) -> str:
    for item in items:
        cleaned = _clean_text(item)
        if cleaned:
            return cleaned
    return ""


def _sentence(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _capitalize_first(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _local_general_idea(home: str, away: str, home_team: dict[str, Any], away_team: dict[str, Any]) -> str:
    home_goal = _avg_known(home_team.get("goals", {}).get("home_avg_scored"), away_team.get("goals", {}).get("away_avg_conceded"))
    away_goal = _avg_known(away_team.get("goals", {}).get("away_avg_scored"), home_team.get("goals", {}).get("home_avg_conceded"))
    if home_goal is not None and away_goal is not None:
        if home_goal >= away_goal + 0.35:
            return f"O jogo tende a passar mais pelo {home}, com o {away} precisando sobreviver sem se expor demais."
        if away_goal >= home_goal + 0.35:
            return f"O {away} tem sinais para incomodar fora, entao o jogo nao parece simples para o mandante."
        return "Os dados apontam equilibrio razoavel, com leitura mais segura em roteiro de jogo do que em vencedor."
    return "os dados sao parciais para montar a leitura, mas ainda nao bastam para cravar um roteiro forte."


def _local_data_quality_read(dossier: dict[str, Any]) -> str:
    quality = dossier.get("data_quality") or {}
    penalty = quality.get("confidence_penalty")
    missing = quality.get("missing_critical_fields") or []
    if penalty is not None:
        base = f"Penalidade interna de confianca: {penalty}/30."
    else:
        base = "Qualidade dos dados parcial."
    if missing:
        base += f" Campos criticos ausentes: {', '.join(str(item) for item in missing[:5])}."
    return base


def _local_team_profiles_read(dossier: dict[str, Any]) -> list[str]:
    rows = []
    for key, label in (("home_team_profile", "Mandante"), ("away_team_profile", "Visitante")):
        profile = dossier.get(key) or {}
        name = profile.get("name") or label
        recent = profile.get("recent_form", {}).get("last_5", {}) if isinstance(profile.get("recent_form"), dict) else {}
        form_string = str(_nested_profile_get(profile, "recent_form", "form_string") or "")
        fallback_record = _record_from_form(form_string)
        attack = profile.get("attack") if isinstance(profile.get("attack"), dict) else {}
        defense = profile.get("defense") if isinstance(profile.get("defense"), dict) else {}
        rows.append(
            f"{name}: últimos 5 com {recent.get('wins') if recent.get('sample_size') else fallback_record['wins']}V/"
            f"{recent.get('draws') if recent.get('sample_size') else fallback_record['draws']}E/"
            f"{recent.get('losses') if recent.get('sample_size') else fallback_record['losses']}D, "
            f"ataque em {attack.get('goals_per_game', 'indisponivel')} gol/jogo e defesa cedendo {defense.get('goals_against_per_game', 'indisponivel')}."
        )
    return rows


def _local_market_assessments(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "home_win": "Mandante vencer",
        "double_chance_home": "Dupla chance mandante",
        "over_1_5": "Over 1.5 gols",
        "over_2_5": "Over 2.5 gols",
        "under_2_5": "Under 2.5 gols",
        "btts": "Ambas marcam",
        "home_team_goal": "Mandante marcar",
        "away_team_goal": "Visitante marcar",
    }
    rows = []
    scores = dossier.get("market_scores") if isinstance(dossier.get("market_scores"), dict) else {}
    for key, item in sorted(scores.items(), key=lambda pair: int((pair[1] or {}).get("score") or 0), reverse=True):
        if not isinstance(item, dict):
            continue
        odds = item.get("odds") if isinstance(item.get("odds"), dict) else {}
        value_note = odds.get("value_label") if odds else "Há tendência técnica, mas não é possível confirmar valor sem preço de mercado."
        rows.append(
            {
                "market": labels.get(key, key),
                "score": int(item.get("score") or 0),
                "confidence": item.get("confidence") or "",
                "reading": item.get("reason") or "",
                "risk": item.get("risk") or "",
                "value_note": value_note,
            }
        )
    return rows[:6]


def _record_from_form(value: str) -> dict[str, int]:
    chars = [char.upper() for char in value if char.upper() in {"W", "D", "L", "V", "E"}][-5:]
    return {
        "wins": sum(1 for char in chars if char in {"W", "V"}),
        "draws": sum(1 for char in chars if char in {"D", "E"}),
        "losses": sum(1 for char in chars if char == "L"),
    }


def _nested_profile_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


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
        ideas.append(
            {
                "market": "escanteios",
                "idea": "olhar linha de escanteios",
                "projection": _corner_projection(corner_avg),
                "projection_analysis": f"a media combinada recente fica perto de {corner_avg:.1f}, entao eu trabalharia com uma faixa, nao com numero cravado.",
                "confidence": "baixa",
                "reason": "amostra recente sugere volume lateral, mas precisa confirmar linha e estilo.",
            }
        )
    return ideas[:4] or [{"market": "sem mercado claro", "idea": "jogo para observacao", "confidence": "baixa", "reason": "os dados nao sustentam uma ideia qualitativa forte."}]


def _corner_projection(corner_avg: float) -> str:
    low = max(0, round(corner_avg - 1))
    high = max(low + 1, round(corner_avg + 1))
    return f"{low} a {high} escanteios"


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
