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
CUP_LEAGUE_IDS = {2, 3, 13}


DOMESTIC_RULES: dict[int, dict[str, int | str]] = {
    39: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    140: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    135: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    78: {"champions_to": 4, "continental_to": 7, "relegation_count": 3, "continental_label": "vaga europeia"},
    61: {"champions_to": 3, "continental_to": 6, "relegation_count": 3, "continental_label": "vaga europeia"},
    88: {"champions_to": 2, "continental_to": 8, "relegation_count": 3, "continental_label": "vaga europeia/playoffs"},
    71: {"champions_to": 6, "continental_to": 12, "relegation_count": 4, "continental_label": "Sul-Americana"},
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
            fixture_date=fixture_date,
            standings=standings,
            schedule=_as_list(home_schedule_response.get("data") if home_schedule_response.get("ok") else None),
        )
        away_summary = self._team_context(
            team_id=fixture.get("away_team_id"),
            team_name=fixture.get("away_team") or "Visitante",
            league_id=league_id,
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
        }

    def _team_context(
        self,
        *,
        team_id: Any,
        team_name: str,
        league_id: int | None,
        fixture_date: datetime | None,
        standings: list[dict[str, Any]],
        schedule: list[dict[str, Any]],
    ) -> dict[str, str | None]:
        calendar = _upcoming_international_summary(team_name, fixture_date, schedule)
        table = _table_objective_summary(team_id, team_name, league_id, standings)

        if calendar and INSUFFICIENT_CONTEXT not in table:
            return {"summary": f"{calendar} {table}", "alert": calendar}
        if calendar:
            return {"summary": calendar, "alert": calendar}
        return {"summary": table, "alert": None}


def _table_objective_summary(
    team_id: Any,
    team_name: str,
    league_id: int | None,
    standings: list[dict[str, Any]],
) -> str:
    row = _find_standing_row(team_id, team_name, standings)
    if not row:
        return f"{team_name}: {INSUFFICIENT_CONTEXT}."

    position = _to_int(row.get("rank") or row.get("position"))
    total = _standing_group_size(row, standings)
    if not position:
        return f"{team_name}: {INSUFFICIENT_CONTEXT}."

    if league_id in CUP_LEAGUE_IDS:
        return f"{team_name}: briga por classificacao no grupo/fase."

    rules = DOMESTIC_RULES.get(league_id or -1)
    if not rules:
        return f"{team_name}: {INSUFFICIENT_CONTEXT}."

    champions_to = int(rules["champions_to"])
    continental_to = int(rules["continental_to"])
    relegation_count = int(rules["relegation_count"])
    continental_label = str(rules["continental_label"])

    if position <= champions_to:
        label = "Libertadores" if league_id == 71 else "Champions"
        return f"{team_name}: briga por {label}."
    if position <= continental_to:
        return f"{team_name}: briga por {continental_label}."
    if total and position >= total - relegation_count + 1:
        return f"{team_name}: luta contra rebaixamento."
    if total:
        return f"{team_name}: meio de tabela."
    return f"{team_name}: {INSUFFICIENT_CONTEXT}."


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


def _is_international_competition(name: str) -> bool:
    normalized = _compact_name(name)
    return any(_compact_name(term) in normalized for term in INTERNATIONAL_COMPETITIONS)


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
