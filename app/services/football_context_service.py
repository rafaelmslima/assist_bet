from __future__ import annotations

from datetime import datetime
from typing import Any


INSUFFICIENT_CONTEXT = "contexto indisponivel"
INTERNATIONAL_COMPETITIONS = (
    "champions league",
    "europa league",
    "conference league",
    "libertadores",
    "sul-americana",
    "sudamericana",
)
CUP_LEAGUE_IDS = {2, 3, 11, 13}


DOMESTIC_RULES: dict[int, dict[str, int | str]] = {
    39: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    140: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    135: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    78: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    61: {"champions_to": 3, "continental_to": 6, "relegation_count": 3, "continental_label": "vaga europeia"},
    88: {"champions_to": 2, "continental_to": 8, "relegation_count": 3, "continental_label": "vaga europeia/playoffs"},
    71: {"champions_to": 6, "continental_to": 12, "relegation_count": 4, "continental_label": "Sul-Americana"},
}
COMPETITIVE_STATES = {
    "champion_locked",
    "title_still_at_risk",
    "title_race",
    "continental_locked",
    "continental_at_risk",
    "continental_race",
    "relegated_locked",
    "relegation_at_risk",
    "safe_midtable",
}


class FootballContextService:
    """Summarizes table objective and upcoming international fixtures."""

    def build_context_summary(
        self,
        *,
        fixture: dict[str, Any],
        standings_response: dict[str, Any],
        home_schedule_response: dict[str, Any],
        away_schedule_response: dict[str, Any],
    ) -> dict[str, Any]:
        league_id = _to_int(fixture.get("league_id"))
        fixture_date = _parse_date(fixture.get("fixture_date"))
        standings = _flatten_standings(standings_response.get("data") if standings_response.get("ok") else None)

        home_summary = self._team_context(
            team_id=fixture.get("home_team_id"),
            team_name=fixture.get("home_team") or "Mandante",
            league_id=league_id,
            fixture_round=fixture.get("round"),
            fixture_date=fixture_date,
            standings=standings,
            schedule=_as_list(home_schedule_response.get("data") if home_schedule_response.get("ok") else None),
        )
        away_summary = self._team_context(
            team_id=fixture.get("away_team_id"),
            team_name=fixture.get("away_team") or "Visitante",
            league_id=league_id,
            fixture_round=fixture.get("round"),
            fixture_date=fixture_date,
            standings=standings,
            schedule=_as_list(away_schedule_response.get("data") if away_schedule_response.get("ok") else None),
        )

        lines = [home_summary["summary"], away_summary["summary"]]
        alerts = [item for item in (home_summary.get("alert"), away_summary.get("alert")) if item]
        return {
            "home_context_summary": home_summary["summary"],
            "away_context_summary": away_summary["summary"],
            "context_alerts": alerts,
            "summary_lines": lines,
            "competitive_states": {
                "home": home_summary.get("competitive_state"),
                "away": away_summary.get("competitive_state"),
            },
        }

    def _team_context(
        self,
        *,
        team_id: Any,
        team_name: str,
        league_id: int | None,
        fixture_round: Any,
        fixture_date: datetime | None,
        standings: list[dict[str, Any]],
        schedule: list[dict[str, Any]],
    ) -> dict[str, str | None]:
        calendar = _upcoming_international_summary(team_name, fixture_date, schedule)
        table_payload = _table_objective_summary(team_id, team_name, league_id, standings, fixture_round)
        table = table_payload["summary"]
        alert = table_payload.get("alert")

        if calendar and INSUFFICIENT_CONTEXT not in table:
            merged_alert = " | ".join(item for item in (calendar, alert) if item)
            return {"summary": f"{calendar} {table}", "alert": merged_alert, "competitive_state": table_payload.get("state")}
        if calendar:
            return {"summary": calendar, "alert": " | ".join(item for item in (calendar, alert) if item), "competitive_state": table_payload.get("state")}
        return {"summary": table, "alert": alert, "competitive_state": table_payload.get("state")}


def _table_objective_summary(
    team_id: Any,
    team_name: str,
    league_id: int | None,
    standings: list[dict[str, Any]],
    fixture_round: Any = None,
) -> dict[str, str | None]:
    row = _find_standing_row(team_id, team_name, standings)
    if not row:
        return {"summary": f"{team_name}: {INSUFFICIENT_CONTEXT}.", "state": None, "alert": None}

    position = _to_int(row.get("rank") or row.get("position"))
    total = _standing_group_size(row, standings)
    if not position:
        return {"summary": f"{team_name}: {INSUFFICIENT_CONTEXT}.", "state": None, "alert": None}

    if league_id in CUP_LEAGUE_IDS:
        return {"summary": _cup_phase_objective(team_name, row, total, fixture_round), "state": None, "alert": None}

    rules = DOMESTIC_RULES.get(league_id or -1)
    if not rules:
        return {"summary": f"{team_name}: {INSUFFICIENT_CONTEXT}.", "state": None, "alert": None}

    return _domestic_table_objective(team_name, league_id, row, standings, rules, total)


def _upcoming_international_summary(
    team_name: str,
    fixture_date: datetime | None,
    schedule: list[dict[str, Any]],
    days: int = 5,
) -> str | None:
    if fixture_date is None:
        return None

    next_game = None
    for item in schedule:
        game_date = _parse_date(_nested_get(item, "fixture", "date") or item.get("fixture_date") or item.get("date"))
        league_name = str(_nested_get(item, "league", "name") or item.get("league") or "")
        if game_date is None:
            continue
        diff = (game_date.date() - fixture_date.date()).days
        if 0 < diff <= days and _is_international_competition(league_name):
            next_game = {"league": league_name, "days": diff}
            break

    if not next_game:
        return None
    return f"{team_name}: jogo de {next_game['league']} em {next_game['days']} dias."


def _domestic_table_objective(
    team_name: str,
    league_id: int | None,
    row: dict[str, Any],
    standings: list[dict[str, Any]],
    rules: dict[str, int | str],
    total: int | None,
) -> dict[str, str | None]:
    position = _to_int(row.get("rank") or row.get("position"))
    points = _row_points(row)
    played = _row_played(row) or _max_played(standings)
    games_remaining = _games_remaining(total, played)
    if position is None or total is None:
        return {"summary": f"{team_name}: {INSUFFICIENT_CONTEXT}.", "state": None, "alert": None}

    champions_to = int(rules["champions_to"])
    continental_to = int(rules["continental_to"])
    relegation_count = int(rules["relegation_count"])
    continental_label = str(rules["continental_label"])
    top_label = "Libertadores" if league_id == 71 else "Champions"
    standings_by_rank = sorted(
        [item for item in standings if _to_int(item.get("rank") or item.get("position")) is not None],
        key=lambda item: _to_int(item.get("rank") or item.get("position")) or 999,
    )
    status = _competitive_status(
        row=row,
        standings=standings_by_rank,
        position=position,
        points=points,
        games_remaining=games_remaining,
        total=total,
        champions_to=champions_to,
        continental_to=continental_to,
        relegation_count=relegation_count,
    )

    state = status["state"]
    if state == "champion_locked":
        return {
            "summary": f"{team_name}: ja campeao matematicamente; objetivo principal cumprido.",
            "state": state,
            "alert": f"ALTA: {team_name} ja campeao; risco de queda de intensidade/rotacao.",
        }
    if state == "title_still_at_risk":
        return {"summary": f"{team_name}: lidera, mas ainda pode perder o titulo matematicamente.", "state": state, "alert": None}
    if state == "title_race":
        return {"summary": f"{team_name}: ainda briga matematicamente pelo titulo.", "state": state, "alert": None}
    if state == "continental_locked":
        label = top_label if position <= champions_to else continental_label
        return {
            "summary": f"{team_name}: ja garantiu vaga em {label} matematicamente.",
            "state": state,
            "alert": f"ALTA: {team_name} com vaga garantida; pode reduzir intensidade.",
        }
    if state == "continental_at_risk":
        label = top_label if position <= champions_to else continental_label
        return {"summary": f"{team_name}: esta em zona de {label}, mas ainda pode perder a vaga.", "state": state, "alert": None}
    if state == "continental_race":
        return {"summary": f"{team_name}: ainda tem chance matematica real de {continental_label}.", "state": state, "alert": None}
    if state == "relegated_locked":
        return {
            "summary": f"{team_name}: ja rebaixado matematicamente.",
            "state": state,
            "alert": f"ALTA: {team_name} ja rebaixado; motivacao e intensidade podem oscilar.",
        }
    if state == "relegation_at_risk":
        relegation_start = total - relegation_count + 1
        if position >= relegation_start:
            return {"summary": f"{team_name}: esta na zona e ainda briga para nao cair.", "state": state, "alert": None}
        return {"summary": f"{team_name}: fora da zona, mas ainda em risco matematico de rebaixamento.", "state": state, "alert": None}

    return {"summary": f"{team_name}: meio de tabela seguro, sem risco matematico relevante.", "state": "safe_midtable", "alert": None}


def _competitive_status(
    *,
    row: dict[str, Any],
    standings: list[dict[str, Any]],
    position: int,
    points: int | None,
    games_remaining: int | None,
    total: int,
    champions_to: int,
    continental_to: int,
    relegation_count: int,
) -> dict[str, str]:
    if points is None or games_remaining is None:
        return {"state": "safe_midtable"}

    relegation_start = total - relegation_count + 1
    leader = standings[0] if standings else None
    leader_points = _row_points(leader or {})
    first_outside_continental = _row_by_rank(standings, continental_to + 1)
    first_safe = _row_by_rank(standings, relegation_start - 1)

    # Title states
    if position == 1:
        strongest_chaser_max = _max_points_among(standings[1:], games_remaining)
        if strongest_chaser_max < points:
            return {"state": "champion_locked"}
        return {"state": "title_still_at_risk"}
    if leader_points is not None and _max_points_for_row(row, games_remaining) >= leader_points:
        return {"state": "title_race"}

    # Continental states
    if position <= continental_to:
        outside_max = _max_points_for_row(first_outside_continental, games_remaining)
        if outside_max < points:
            return {"state": "continental_locked"}
        return {"state": "continental_at_risk"}
    continental_cut = _row_by_rank(standings, continental_to)
    continental_cut_points = _row_points(continental_cut or {})
    if continental_cut_points is not None and _max_points_for_row(row, games_remaining) >= continental_cut_points:
        return {"state": "continental_race"}

    # Relegation states
    if position >= relegation_start:
        safe_points = _row_points(first_safe or {})
        if safe_points is not None and _max_points_for_row(row, games_remaining) < safe_points:
            return {"state": "relegated_locked"}
        return {"state": "relegation_at_risk"}
    if _max_points_among(standings[relegation_start - 1 :], games_remaining) >= points:
        return {"state": "relegation_at_risk"}
    return {"state": "safe_midtable"}


def _max_points_for_row(row: dict[str, Any] | None, games_remaining: int) -> int:
    if not isinstance(row, dict):
        return -1
    row_points = _row_points(row)
    if row_points is None:
        return -1
    return row_points + games_remaining * 3


def _max_points_among(rows: list[dict[str, Any]], games_remaining: int) -> int:
    values = [_max_points_for_row(row, games_remaining) for row in rows]
    return max(values) if values else -1


def _flatten_standings(data: Any) -> list[dict[str, Any]]:
    rows = []
    for item in _as_list(data):
        league = item.get("league") if isinstance(item.get("league"), dict) else item
        groups = league.get("standings") if isinstance(league, dict) else None
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, list):
                    for row in group:
                        if isinstance(row, dict):
                            enriched = dict(row)
                            enriched["_group_size"] = len(group)
                            rows.append(enriched)
                elif isinstance(group, dict):
                    rows.append(group)
        elif isinstance(item, dict) and ("rank" in item or "position" in item):
            rows.append(item)
    return rows


def _find_standing_row(team_id: Any, team_name: str, standings: list[dict[str, Any]]) -> dict[str, Any] | None:
    target_id = str(team_id)
    target_name = _compact_name(team_name)
    for row in standings:
        team = row.get("team") if isinstance(row.get("team"), dict) else {}
        row_id = str(team.get("id") or row.get("team_id") or "")
        row_name = _compact_name(str(team.get("name") or row.get("team") or row.get("team_name") or ""))
        if row_id and row_id == target_id:
            return row
        if row_name and (row_name == target_name or row_name in target_name or target_name in row_name):
            return row
    return None


def _standing_group_size(row: dict[str, Any], standings: list[dict[str, Any]]) -> int | None:
    explicit = _to_int(row.get("_group_size") or row.get("total_teams"))
    if explicit:
        return explicit
    return len(standings) if standings else None


def _row_points(row: dict[str, Any]) -> int | None:
    return _to_int(row.get("points") or row.get("pts"))


def _row_played(row: dict[str, Any]) -> int | None:
    return _to_int(_nested_get(row, "all", "played") or row.get("played") or row.get("matches_played"))


def _max_played(standings: list[dict[str, Any]]) -> int | None:
    played_values = [_row_played(row) for row in standings]
    known = [value for value in played_values if value is not None]
    return max(known) if known else None


def _games_remaining(total: int | None, played: int | None) -> int | None:
    if total is None or played is None:
        return None
    scheduled = (total - 1) * 2
    return max(0, scheduled - played)


def _distance_to_continental(row: dict[str, Any], standings: list[dict[str, Any]], continental_to: int) -> int | None:
    points = _row_points(row)
    target = _row_by_rank(standings, continental_to)
    target_points = _row_points(target or {})
    if points is None or target_points is None:
        return None
    return max(0, target_points - points)


def _distance_to_relegation(row: dict[str, Any], standings: list[dict[str, Any]], relegation_start: int) -> int | None:
    points = _row_points(row)
    target = _row_by_rank(standings, relegation_start)
    target_points = _row_points(target or {})
    if points is None or target_points is None:
        return None
    return max(0, points - target_points)


def _row_by_rank(standings: list[dict[str, Any]], rank: int) -> dict[str, Any] | None:
    for row in standings:
        if _to_int(row.get("rank") or row.get("position")) == rank:
            return row
    return None


def _remaining_suffix(games_remaining: int | None) -> str:
    if games_remaining is None:
        return ""
    return f"; {games_remaining} jogos restantes"


def _is_international_competition(name: str) -> bool:
    normalized = _compact_name(name)
    return any(_compact_name(term) in normalized for term in INTERNATIONAL_COMPETITIONS)


def _cup_phase_objective(team_name: str, row: dict[str, Any], total: int | None, fixture_round: Any) -> str:
    phase = _phase_from_round(fixture_round)
    if phase is not None:
        return f"{team_name}: {phase}"

    if total and total <= 4:
        position = _to_int(row.get("rank") or row.get("position"))
        if position is not None:
            if position <= 2:
                return f"{team_name}: briga por classificacao no grupo; hoje esta em zona de classificacao."
            return f"{team_name}: briga por classificacao no grupo; hoje esta fora da zona."
    return f"{team_name}: fase internacional ativa, mas sem round detalhado na API."


def _phase_from_round(value: Any) -> str | None:
    if not value:
        return None
    round_name = _compact_name(str(value))
    if "final" in round_name and "semi" not in round_name and "quarter" not in round_name:
        return "jogo de final; decisao direta de titulo."
    if "semi" in round_name:
        return "briga por vaga na final (semi-final)."
    if "quarter" in round_name or "quartas" in round_name:
        return "briga por vaga na semi-final (quartas de final)."
    if "round of 16" in round_name or "oitavas" in round_name:
        return "mata-mata de oitavas; confronto eliminatorio."
    if "playoff" in round_name or "play offs" in round_name:
        return "fase de playoff eliminatorio."
    if "group" in round_name or "grupo" in round_name:
        return "fase de grupos; disputa por zona de classificacao."
    return f"fase atual: {str(value)}."


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested = value.get("response")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_name(value: str) -> str:
    return " ".join(value.strip().lower().replace("-", " ").split())
