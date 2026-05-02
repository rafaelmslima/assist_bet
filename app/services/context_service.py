from __future__ import annotations

from datetime import datetime
from typing import Any


INSUFFICIENT_DATA = "dados insuficientes"
INTERNATIONAL_COMPETITIONS = (
    "champions",
    "libertadores",
    "sul-americana",
    "sudamericana",
    "europa league",
    "conference league",
    "internacional",
)


class ContextService:
    """Builds situational context such as rest, motivation, travel and rotation risk."""

    def analyze_fixture_context(
        self,
        fixture: dict[str, Any],
        team_schedule: dict[str, Any] | list[dict[str, Any]],
        injuries: dict[str, Any] | list[dict[str, Any]] | None = None,
        standings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sport = str(fixture.get("sport") or "").lower()
        if sport == "nba" or sport == "basketball":
            return self._analyze_nba_context(fixture, team_schedule, injuries, standings)
        return self._analyze_football_context(fixture, team_schedule, injuries, standings)

    def build_context(self, fixture: dict) -> dict:
        """Backward-compatible wrapper for older service calls."""
        return self.analyze_fixture_context(fixture=fixture, team_schedule={})

    def _analyze_football_context(
        self,
        fixture: dict[str, Any],
        team_schedule: dict[str, Any] | list[dict[str, Any]],
        injuries: dict[str, Any] | list[dict[str, Any]] | None,
        standings: dict[str, Any] | None,
    ) -> dict[str, Any]:
        fixture_date = _parse_date(fixture.get("fixture_date") or fixture.get("date") or fixture.get("starts_at"))
        schedule = _normalize_schedule(team_schedule)
        alerts: list[str] = []

        venue_context = _football_venue_context(fixture)
        if venue_context != INSUFFICIENT_DATA:
            alerts.append(venue_context)

        recent_game = _has_recent_game(schedule, fixture_date, days=4)
        international_game = _has_upcoming_international_game(schedule, fixture_date, days=5)
        standings_context = _football_standings_context(fixture, standings)
        rivalry = fixture.get("rivalry") or fixture.get("is_derby") or fixture.get("classic")
        injury_alerts = _injury_alerts(injuries)

        if recent_game["has_recent_game"]:
            alerts.append(f"jogo recente há {recent_game['days_since_game']} dias")
        if international_game["has_international_game"]:
            alerts.append("jogo internacional em até 5 dias")
        if standings_context["alert"] != INSUFFICIENT_DATA:
            alerts.append(standings_context["alert"])
        if rivalry:
            alerts.append("clássico/rivalidade informada")
        alerts.extend(injury_alerts)

        fatigue_risk = _risk_level(recent_game["has_recent_game"], international_game["has_international_game"])
        rotation_risk = _risk_level(
            international_game["has_international_game"],
            bool(injury_alerts),
            fixture.get("already_qualified") is True,
        )
        motivation_level = _motivation_level(
            standings_context["motivation"],
            bool(rivalry),
            fixture.get("title_race") is True,
            fixture.get("relegation_risk") is True,
            fixture.get("continental_spot_race") is True,
        )
        context_score = _context_score(fatigue_risk, rotation_risk, motivation_level)

        partial = _is_partial(fixture_date, schedule, standings)
        if partial:
            alerts.append("análise parcial por falta de dados")

        return {
            "context_score": context_score,
            "fatigue_risk": fatigue_risk,
            "rotation_risk": rotation_risk,
            "motivation_level": motivation_level,
            "alerts": alerts or ["sem alertas relevantes com os dados atuais"],
            "textual_summary": _summary(context_score, fatigue_risk, rotation_risk, motivation_level, partial),
        }

    def _analyze_nba_context(
        self,
        fixture: dict[str, Any],
        team_schedule: dict[str, Any] | list[dict[str, Any]],
        injuries: dict[str, Any] | list[dict[str, Any]] | None,
        standings: dict[str, Any] | None,
    ) -> dict[str, Any]:
        fixture_date = _parse_date(fixture.get("fixture_date") or fixture.get("date") or fixture.get("starts_at"))
        schedule = _normalize_schedule(team_schedule)
        alerts: list[str] = []

        back_to_back = _is_back_to_back(schedule, fixture_date)
        three_in_four = _is_three_games_in_four_nights(schedule, fixture_date)
        long_travel = bool(fixture.get("long_travel") or fixture.get("travel_long") or fixture.get("travel_distance_km", 0) >= 1200)
        minutes_alert = _minutes_alert(fixture)
        rest_alert = _comparative_rest_alert(fixture)
        standings_alert = _nba_standings_alert(standings)
        injury_alerts = _injury_alerts(injuries)

        if back_to_back:
            alerts.append("back-to-back")
        if three_in_four:
            alerts.append("3 jogos em 4 noites")
        if long_travel:
            alerts.append("viagem longa")
        if minutes_alert:
            alerts.append(minutes_alert)
        if rest_alert:
            alerts.append(rest_alert)
        if standings_alert != INSUFFICIENT_DATA:
            alerts.append(standings_alert)
        alerts.extend(injury_alerts)

        fatigue_risk = _risk_level(back_to_back, three_in_four, long_travel, bool(minutes_alert))
        rotation_risk = _risk_level(back_to_back, bool(injury_alerts), bool(minutes_alert))
        motivation_level = _motivation_level(
            fixture.get("importance"),
            fixture.get("playoff_race") is True,
            fixture.get("conference_position_pressure") is True,
        )
        context_score = _context_score(fatigue_risk, rotation_risk, motivation_level)

        partial = _is_partial(fixture_date, schedule, standings)
        if partial:
            alerts.append("análise parcial por falta de dados")

        return {
            "context_score": context_score,
            "fatigue_risk": fatigue_risk,
            "rotation_risk": rotation_risk,
            "motivation_level": motivation_level,
            "alerts": alerts or ["sem alertas relevantes com os dados atuais"],
            "textual_summary": _summary(context_score, fatigue_risk, rotation_risk, motivation_level, partial),
        }


def _normalize_schedule(team_schedule: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(team_schedule, list):
        return team_schedule
    for key in ("games", "fixtures", "schedule", "matches"):
        value = team_schedule.get(key)
        if isinstance(value, list):
            return value
    return []


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _game_date(game: dict[str, Any]) -> datetime | None:
    return _parse_date(game.get("fixture_date") or game.get("date") or game.get("starts_at") or game.get("game_date"))


def _has_recent_game(schedule: list[dict[str, Any]], fixture_date: datetime | None, days: int) -> dict[str, Any]:
    if fixture_date is None:
        return {"has_recent_game": False, "days_since_game": None}

    recent_days = []
    for game in schedule:
        game_date = _game_date(game)
        if game_date is None or game_date >= fixture_date:
            continue
        diff = (fixture_date.date() - game_date.date()).days
        if 0 < diff <= days:
            recent_days.append(diff)

    return {
        "has_recent_game": bool(recent_days),
        "days_since_game": min(recent_days) if recent_days else None,
    }


def _has_upcoming_international_game(
    schedule: list[dict[str, Any]],
    fixture_date: datetime | None,
    days: int,
) -> dict[str, Any]:
    if fixture_date is None:
        return {"has_international_game": False}

    for game in schedule:
        game_date = _game_date(game)
        competition = str(game.get("competition") or game.get("league") or "").lower()
        if game_date is None or game_date <= fixture_date:
            continue
        diff = (game_date.date() - fixture_date.date()).days
        if 0 < diff <= days and any(name in competition for name in INTERNATIONAL_COMPETITIONS):
            return {"has_international_game": True, "next_game": game}

    return {"has_international_game": False}


def _is_back_to_back(schedule: list[dict[str, Any]], fixture_date: datetime | None) -> bool:
    return _has_recent_game(schedule, fixture_date, days=1)["has_recent_game"]


def _is_three_games_in_four_nights(schedule: list[dict[str, Any]], fixture_date: datetime | None) -> bool:
    if fixture_date is None:
        return False
    games_in_window = 1
    for game in schedule:
        game_date = _game_date(game)
        if game_date is None:
            continue
        diff = abs((fixture_date.date() - game_date.date()).days)
        if 0 < diff <= 3:
            games_in_window += 1
    return games_in_window >= 3


def _football_venue_context(fixture: dict[str, Any]) -> str:
    home_team = fixture.get("home_team") or fixture.get("home_team_name")
    team = fixture.get("team") or fixture.get("team_name")
    if not home_team or not team:
        return INSUFFICIENT_DATA
    return "jogo em casa" if str(home_team).lower() == str(team).lower() else "jogo fora"


def _football_standings_context(fixture: dict[str, Any], standings: dict[str, Any] | None) -> dict[str, str]:
    if not standings:
        return {"alert": INSUFFICIENT_DATA, "motivation": INSUFFICIENT_DATA}

    position = standings.get("position") or standings.get("rank")
    status = standings.get("status") or standings.get("objective") or fixture.get("motivation")
    already_qualified = standings.get("already_qualified") or fixture.get("already_qualified")

    if already_qualified:
        return {"alert": "time já classificado para competição internacional", "motivation": "média"}
    if status:
        return {"alert": f"motivação informada: {status}", "motivation": str(status)}
    if isinstance(position, int):
        if position <= 3:
            return {"alert": "briga por título/vaga alta", "motivation": "alta"}
        if position <= 7:
            return {"alert": "briga por vaga continental", "motivation": "alta"}
        if position >= 17:
            return {"alert": "risco de rebaixamento", "motivation": "alta"}
    return {"alert": INSUFFICIENT_DATA, "motivation": INSUFFICIENT_DATA}


def _nba_standings_alert(standings: dict[str, Any] | None) -> str:
    if not standings:
        return INSUFFICIENT_DATA
    conference_position = standings.get("conference_position") or standings.get("rank")
    if isinstance(conference_position, int):
        if conference_position <= 6:
            return "zona direta de playoffs"
        if conference_position <= 10:
            return "briga por play-in"
        return "fora da zona de play-in"
    importance = standings.get("importance") or standings.get("objective")
    return str(importance) if importance else INSUFFICIENT_DATA


def _injury_alerts(injuries: dict[str, Any] | list[dict[str, Any]] | None) -> list[str]:
    if not injuries:
        return []
    if isinstance(injuries, list):
        if not injuries:
            return []
        return [f"{len(injuries)} lesões/suspensões informadas"]

    players = injuries.get("players")
    total = injuries.get("total")
    if total is None and isinstance(players, list):
        total = len(players)
    key_players = injuries.get("key_players") or injuries.get("important_players")
    alerts = []
    if total:
        alerts.append(f"{total} lesões/suspensões informadas")
    if key_players:
        alerts.append("desfalques em jogadores importantes")
    return alerts


def _minutes_alert(fixture: dict[str, Any]) -> str | None:
    minutes = fixture.get("key_players_minutes") or fixture.get("main_players_minutes")
    if not isinstance(minutes, list) or not minutes:
        return None
    high_minutes = [value for value in minutes if isinstance(value, (int, float)) and value >= 36]
    if len(high_minutes) >= 2:
        return "minutagem alta dos principais jogadores"
    return None


def _comparative_rest_alert(fixture: dict[str, Any]) -> str | None:
    home_rest = fixture.get("home_rest_days")
    away_rest = fixture.get("away_rest_days")
    if not isinstance(home_rest, int) or not isinstance(away_rest, int):
        return None
    if home_rest - away_rest >= 2:
        return "mandante chega mais descansado"
    if away_rest - home_rest >= 2:
        return "visitante chega mais descansado"
    return "descanso semelhante entre os times"


def _risk_level(*flags: bool) -> str:
    count = sum(1 for flag in flags if flag)
    if count >= 2:
        return "alto"
    if count == 1:
        return "médio"
    return "baixo"


def _motivation_level(*signals: Any) -> str:
    known_signals = [signal for signal in signals if signal not in (None, False, "", INSUFFICIENT_DATA)]
    if not known_signals:
        return INSUFFICIENT_DATA

    joined = " ".join(str(signal).lower() for signal in known_signals)
    high_terms = ("alta", "title", "título", "continental", "rebaixamento", "playoff", "play-in", "vaga")
    low_terms = ("baixa", "classificado", "sem objetivo")
    if any(term in joined for term in high_terms):
        return "alta"
    if any(term in joined for term in low_terms):
        return "baixa"
    return "média"


def _context_score(fatigue_risk: str, rotation_risk: str, motivation_level: str) -> int | str:
    if motivation_level == INSUFFICIENT_DATA:
        return INSUFFICIENT_DATA

    score = 50
    score += {"alta": 20, "média": 10, "baixa": -10}.get(motivation_level, 0)
    score -= {"alto": 20, "médio": 10, "baixo": 0}.get(fatigue_risk, 0)
    score -= {"alto": 15, "médio": 8, "baixo": 0}.get(rotation_risk, 0)
    return max(0, min(100, score))


def _is_partial(
    fixture_date: datetime | None,
    schedule: list[dict[str, Any]],
    standings: dict[str, Any] | None,
) -> bool:
    return fixture_date is None or not schedule or not standings


def _summary(
    context_score: int | str,
    fatigue_risk: str,
    rotation_risk: str,
    motivation_level: str,
    partial: bool,
) -> str:
    prefix = "Análise parcial. " if partial else ""
    return (
        f"{prefix}Contexto {context_score}; fadiga {fatigue_risk}; "
        f"rotação {rotation_risk}; motivação {motivation_level}."
    )
