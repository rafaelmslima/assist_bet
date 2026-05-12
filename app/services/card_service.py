from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.analysis_service import AnalysisService


INSUFFICIENT_DATA = "dados insuficientes"


class CardService:
    """Generates Telegram-ready football context cards."""

    def __init__(self, analysis_service: AnalysisService | None = None) -> None:
        self.analysis_service = analysis_service or AnalysisService()

    def generate_pre_match_card(self, fixture_data: dict[str, Any]) -> str:
        fixture = fixture_data.get("fixture", fixture_data)
        home_team = fixture_data.get("home_team_data") or fixture_data.get("home_team") or {}
        away_team = fixture_data.get("away_team_data") or fixture_data.get("away_team") or {}
        context = fixture_data.get("context") or fixture_data.get("fixture_context") or {}
        props = _as_list(fixture_data.get("props") or fixture_data.get("top_props"))

        matchup = fixture_data.get("matchup_analysis")
        if matchup is None and home_team and away_team:
            matchup = self.analysis_service.analyze_matchup(home_team, away_team, context)
        matchup = matchup or {}

        lines = [
            "CARD DE CONTEXTO",
            "",
            self._fixture_section(fixture),
            "",
            self._form_section(home_team, away_team),
            "",
            self._home_away_section(home_team, away_team),
            "",
            self._matchup_section(matchup),
            "",
            self._context_section(context),
        ]
        if props:
            lines.extend(["", self._props_section(props)])
        lines.extend(["", self._final_alerts_section(fixture_data, context)])
        return "\n".join(line for line in lines if line is not None)

    def _fixture_section(self, fixture: dict[str, Any]) -> str:
        home = _get(fixture, "home_team", "home_team_name", "mandante")
        away = _get(fixture, "away_team", "away_team_name", "visitante")
        competition = _get(fixture, "competition", "league", "competicao")
        fixture_date = _format_date(_get(fixture, "fixture_date", "date", "starts_at"))

        return (
            "Jogo\n"
            f"{home} x {away}\n"
            f"Competicao: {competition}\n"
            f"Data: {fixture_date}\n"
            f"Mandante: {home}\n"
            f"Visitante: {away}"
        )

    def _form_section(self, home_team: dict[str, Any], away_team: dict[str, Any]) -> str:
        home_name = _get(home_team, "name", "team_name", default="Mandante")
        away_name = _get(away_team, "name", "team_name", default="Visitante")
        return (
            "Forma recente\n"
            f"{home_name}: {_form(home_team)}\n"
            f"{away_name}: {_form(away_team)}"
        )

    def _home_away_section(self, home_team: dict[str, Any], away_team: dict[str, Any]) -> str:
        home_split = _split_text(home_team, "home_avg_scored", "home_avg_conceded")
        away_split = _split_text(away_team, "away_avg_scored", "away_avg_conceded")
        return (
            "Casa/Fora\n"
            f"Mandante em casa: {home_split}\n"
            f"Visitante fora: {away_split}"
        )

    def _matchup_section(self, matchup: dict[str, Any]) -> str:
        betting_read = matchup.get("betting_read")
        watch_points = matchup.get("watch_points")
        if isinstance(betting_read, list) and betting_read:
            lines = ["Leitura do confronto"]
            lines.extend(f"- {item}" for item in betting_read[:3])
            if isinstance(watch_points, list) and watch_points:
                lines.append("Pontos de atencao")
                lines.extend(f"- {item}" for item in watch_points[:3])
            return "\n".join(lines)

        strengths = matchup.get("pontos_fortes") or matchup.get("mercados_potenciais") or INSUFFICIENT_DATA
        weaknesses = matchup.get("pontos_fracos") or matchup.get("alertas") or INSUFFICIENT_DATA
        tactical_fit = matchup.get("encaixe_tatico") or matchup.get("leitura_de_matchup") or INSUFFICIENT_DATA

        return (
            "Matchup\n"
            f"Pontos fortes: {_as_text(strengths)}\n"
            f"Pontos fracos: {_as_text(weaknesses)}\n"
            f"Encaixe tatico: {_as_text(tactical_fit)}"
        )

    def _context_section(self, context: dict[str, Any]) -> str:
        football_context = context.get("football_context") if isinstance(context.get("football_context"), dict) else {}
        summary_lines = football_context.get("summary_lines") or []
        if summary_lines:
            return "Contexto\n" + "\n".join(f"- {line}" for line in summary_lines[:4])
        return "Contexto\nSem dados confiaveis de tabela, calendario, escalacoes e desfalques nesta chamada."

    def _props_section(self, props: list[dict[str, Any]]) -> str:
        if not props:
            return "Jogadores\nDados insuficientes"

        lines = ["Jogadores em atencao"]
        for prop in props[:5]:
            player = _get(prop, "player", "player_name", "name")
            market = _get(prop, "market", "market_type")
            risk = _get(prop, "risk_level", "risk", "risco", default=INSUFFICIENT_DATA)
            lines.append(f"{player}: {market} | risco: {risk}")
        return "\n".join(lines)

    def _final_alerts_section(self, fixture_data: dict[str, Any], context: dict[str, Any]) -> str:
        alerts = list(fixture_data.get("final_alerts") or [])
        context_alerts = context.get("alerts")
        if isinstance(context_alerts, list):
            alerts.extend(context_alerts)
        if not fixture_data.get("lineups_confirmed"):
            alerts.append("confirmar escalacao")
        if context.get("rotation_risk") in {"alto", "medio"}:
            alerts.append("cuidado com rotacao")
        alerts.append("tratar ideias de mercado como hipotese, nao como certeza")

        unique_alerts = []
        for alert in alerts:
            if alert and alert not in unique_alerts:
                unique_alerts.append(alert)

        return "Alertas finais\n" + "\n".join(f"- {alert}" for alert in unique_alerts[:6])


def generate_pre_match_card(fixture_data: dict[str, Any]) -> str:
    return CardService().generate_pre_match_card(fixture_data)


def _get(data: dict[str, Any], *keys: str, default: str = INSUFFICIENT_DATA) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "items", "props"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _form(data: dict[str, Any]) -> str:
    form = _get(data, "last_5_form", "recent_form", "form", "recent_results")
    if isinstance(form, list):
        return " ".join(str(item) for item in form[-5:])
    if isinstance(form, str):
        chars = [char.upper() for char in form if char.upper() in {"W", "D", "L", "V", "E"}]
        return " ".join(chars[-5:]) if chars else form
    return str(form)


def _split_text(data: dict[str, Any], scored_key: str, conceded_key: str) -> str:
    scored = data.get(scored_key)
    conceded = data.get(conceded_key)
    if scored is None and conceded is None:
        return INSUFFICIENT_DATA
    scored_text = f"marca {scored}" if scored is not None else "ataque sem dados"
    conceded_text = f"sofre {conceded}" if conceded is not None else "defesa sem dados"
    return f"{scored_text}; {conceded_text}"


def _as_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return INSUFFICIENT_DATA
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else INSUFFICIENT_DATA
    return str(value)


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return value
    return INSUFFICIENT_DATA
