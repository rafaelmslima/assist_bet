from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.integrations.api_football_client import ApiFootballClient


INSUFFICIENT_DATA = "dados insuficientes"


@dataclass(frozen=True)
class FixturePlayerContext:
    fixture_id: str
    fixture: dict[str, Any]
    players: list[dict[str, Any]]
    injuries: list[dict[str, Any]]
    lineups: dict[str, Any]
    predictions: dict[str, Any]
    coverage: dict[str, bool]
    data_quality: list[str]


class FootballPlayerService:
    """Builds fixture-scoped football player data from API-Football."""

    def __init__(self, client: ApiFootballClient | None = None) -> None:
        self.client = client or ApiFootballClient()

    def build_fixture_player_context(self, fixture: dict[str, Any]) -> FixturePlayerContext:
        fixture_id = str(fixture.get("fixture_id") or "")
        home_team_id = fixture.get("home_team_id")
        away_team_id = fixture.get("away_team_id")
        league_id = fixture.get("league_id")
        season = fixture.get("season")
        data_quality: list[str] = []

        coverage = self._get_coverage(league_id, season)
        if not coverage:
            data_quality.append("nao consegui validar a cobertura da liga na API-Football")

        lineups = self._get_lineups(fixture_id, coverage, data_quality)
        injuries = self._get_injuries(fixture_id, coverage, data_quality)
        predictions = self._get_predictions(fixture_id, coverage, data_quality)

        players = self._get_fixture_players(fixture_id, coverage, data_quality)
        if not players:
            players = self._get_season_players(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                league_id=league_id,
                season=season,
                lineups=lineups,
                injuries=injuries,
                data_quality=data_quality,
            )

        if not players:
            data_quality.append("sem estatisticas de jogadores para este jogo/temporada")

        players = _apply_lineup_and_injury_context(players, lineups, injuries)
        return FixturePlayerContext(
            fixture_id=fixture_id,
            fixture=fixture,
            players=players,
            injuries=injuries,
            lineups=lineups,
            predictions=predictions,
            coverage=coverage,
            data_quality=_unique(data_quality),
        )

    def _get_coverage(self, league_id: Any, season: Any) -> dict[str, bool]:
        if league_id in (None, "") or season in (None, ""):
            return {}

        response = self.client.get_league_coverage(league_id, season)
        if not response.get("ok"):
            return {}

        items = _as_list(response.get("data"))
        if not items:
            return {}

        seasons = items[0].get("seasons") if isinstance(items[0].get("seasons"), list) else []
        selected = next((item for item in seasons if str(item.get("year")) == str(season)), None)
        coverage = selected.get("coverage") if isinstance(selected, dict) else None
        if not isinstance(coverage, dict):
            return {}

        fixture_coverage = coverage.get("fixtures") if isinstance(coverage.get("fixtures"), dict) else {}
        return {
            "events": bool(fixture_coverage.get("events")),
            "lineups": bool(fixture_coverage.get("lineups")),
            "fixture_statistics": bool(fixture_coverage.get("statistics_fixtures")),
            "player_statistics": bool(fixture_coverage.get("statistics_players")),
            "standings": bool(coverage.get("standings")),
            "players": bool(coverage.get("players")),
            "top_scorers": bool(coverage.get("top_scorers")),
            "top_assists": bool(coverage.get("top_assists")),
            "top_cards": bool(coverage.get("top_cards")),
            "injuries": bool(coverage.get("injuries")),
            "predictions": bool(coverage.get("predictions")),
            "odds": bool(coverage.get("odds")),
        }

    def _get_lineups(self, fixture_id: str, coverage: dict[str, bool], data_quality: list[str]) -> dict[str, Any]:
        if coverage and not coverage.get("lineups"):
            data_quality.append("lineups sem cobertura para esta liga/temporada")
            return {"confirmed": False, "teams": {}}

        response = self.client.get_fixture_lineups(int(fixture_id)) if fixture_id else {"ok": False}
        if not response.get("ok"):
            data_quality.append("nao consegui buscar escalacoes")
            return {"confirmed": False, "teams": {}}

        raw_lineups = _as_list(response.get("data"))
        if not raw_lineups:
            data_quality.append("escalacoes ainda nao disponiveis")
            return {"confirmed": False, "teams": {}}

        teams: dict[str, dict[str, Any]] = {}
        for item in raw_lineups:
            team = item.get("team") if isinstance(item.get("team"), dict) else {}
            team_id = str(team.get("id") or "")
            if not team_id:
                continue
            starters = [_lineup_player(entry) for entry in item.get("startXI") or []]
            substitutes = [_lineup_player(entry) for entry in item.get("substitutes") or []]
            teams[team_id] = {
                "team": team,
                "formation": item.get("formation"),
                "starters": [player for player in starters if player],
                "substitutes": [player for player in substitutes if player],
            }

        return {"confirmed": bool(teams), "teams": teams}

    def _get_injuries(self, fixture_id: str, coverage: dict[str, bool], data_quality: list[str]) -> list[dict[str, Any]]:
        if coverage and not coverage.get("injuries"):
            data_quality.append("injuries sem cobertura para esta liga/temporada")
            return []

        response = self.client.get_injuries(fixture_id=fixture_id) if fixture_id else {"ok": False}
        if not response.get("ok"):
            data_quality.append("nao consegui buscar desfalques")
            return []

        injuries = [_normalize_injury(item) for item in _as_list(response.get("data"))]
        return [item for item in injuries if item.get("player_name")]

    def _get_predictions(self, fixture_id: str, coverage: dict[str, bool], data_quality: list[str]) -> dict[str, Any]:
        if coverage and not coverage.get("predictions"):
            return {}

        response = self.client.get_predictions(fixture_id) if fixture_id else {"ok": False}
        if not response.get("ok"):
            return {}

        items = _as_list(response.get("data"))
        return items[0] if items else {}

    def _get_fixture_players(self, fixture_id: str, coverage: dict[str, bool], data_quality: list[str]) -> list[dict[str, Any]]:
        if coverage and not coverage.get("player_statistics"):
            data_quality.append("estatisticas de jogadores por partida sem cobertura")
            return []

        response = self.client.get_fixture_players(fixture_id) if fixture_id else {"ok": False}
        if not response.get("ok"):
            data_quality.append("nao consegui buscar estatisticas individuais da partida")
            return []

        players = _normalize_fixture_players(_as_list(response.get("data")))
        if players:
            data_quality.append("estatisticas individuais da partida disponiveis")
        return players

    def _get_season_players(
        self,
        *,
        home_team_id: Any,
        away_team_id: Any,
        league_id: Any,
        season: Any,
        lineups: dict[str, Any],
        injuries: list[dict[str, Any]],
        data_quality: list[str],
    ) -> list[dict[str, Any]]:
        if season in (None, ""):
            return []

        players: list[dict[str, Any]] = []
        for team_id in (home_team_id, away_team_id):
            if team_id in (None, ""):
                continue
            team_players = self._fetch_team_players(team_id, season, league_id)
            players.extend(team_players)

        if players:
            data_quality.append("usando estatisticas de temporada dos jogadores")
        else:
            data_quality.append("sem estatisticas de temporada dos jogadores")

        lineup_ids = _lineup_player_ids(lineups)
        injury_ids = {str(item.get("player_id")) for item in injuries if item.get("player_id")}
        if lineup_ids:
            players = [player for player in players if str(player.get("player_id")) in lineup_ids]
            data_quality.append("shortlist filtrada por escalacao confirmada")
        elif injury_ids:
            players = [player for player in players if str(player.get("player_id")) not in injury_ids]

        return players

    def _fetch_team_players(self, team_id: Any, season: Any, league_id: Any) -> list[dict[str, Any]]:
        players: list[dict[str, Any]] = []
        page = 1
        max_pages = 3
        while page <= max_pages:
            response = self.client.get_players(team_id=team_id, season=season, league_id=league_id, page=page)
            if not response.get("ok"):
                break

            players.extend(_normalize_season_players(_as_list(response.get("data"))))
            paging = response.get("meta", {}).get("paging") or {}
            total_pages = int(paging.get("total") or page)
            if page >= total_pages:
                break
            page += 1

        return players


def _normalize_fixture_players(raw_teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for team_item in raw_teams:
        team = team_item.get("team") if isinstance(team_item.get("team"), dict) else {}
        for item in team_item.get("players") or []:
            player = item.get("player") if isinstance(item.get("player"), dict) else {}
            stats = item.get("statistics") if isinstance(item.get("statistics"), list) else []
            stat = stats[0] if stats and isinstance(stats[0], dict) else {}
            normalized.append(_normalize_player_stat(player, stat, team, source="fixture"))
    return [item for item in normalized if item.get("player_name")]


def _normalize_season_players(raw_players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_players:
        player = item.get("player") if isinstance(item.get("player"), dict) else {}
        for stat in item.get("statistics") or []:
            if not isinstance(stat, dict):
                continue
            team = stat.get("team") if isinstance(stat.get("team"), dict) else {}
            normalized.append(_normalize_player_stat(player, stat, team, source="season"))
    return [item for item in normalized if item.get("player_name")]


def _normalize_player_stat(player: dict[str, Any], stat: dict[str, Any], team: dict[str, Any], source: str) -> dict[str, Any]:
    games = stat.get("games") if isinstance(stat.get("games"), dict) else {}
    shots = stat.get("shots") if isinstance(stat.get("shots"), dict) else {}
    goals = stat.get("goals") if isinstance(stat.get("goals"), dict) else {}
    passes = stat.get("passes") if isinstance(stat.get("passes"), dict) else {}
    tackles = stat.get("tackles") if isinstance(stat.get("tackles"), dict) else {}
    cards = stat.get("cards") if isinstance(stat.get("cards"), dict) else {}

    appearances = _to_float(games.get("appearences") or games.get("appearances")) or (1.0 if source == "fixture" else None)
    minutes = _to_float(games.get("minutes"))
    yellow = _to_float(cards.get("yellow")) or 0.0
    red = _to_float(cards.get("red")) or 0.0
    total_cards = yellow + red

    return {
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "position": games.get("position") or player.get("position"),
        "rating": _to_float(games.get("rating")),
        "appearances": appearances,
        "minutes": minutes,
        "goals": _to_float(goals.get("total")),
        "assists": _to_float(goals.get("assists")),
        "shots": _to_float(shots.get("total")),
        "shots_on_target": _to_float(shots.get("on")),
        "key_passes": _to_float(passes.get("key")),
        "tackles": _to_float(tackles.get("total")),
        "cards": total_cards if total_cards > 0 else None,
        "injured": bool(player.get("injured")),
        "source": source,
        "starter": None,
        "substitute": None,
        "injury_reason": None,
    }


def _normalize_injury(raw: dict[str, Any]) -> dict[str, Any]:
    player = raw.get("player") if isinstance(raw.get("player"), dict) else {}
    team = raw.get("team") if isinstance(raw.get("team"), dict) else {}
    return {
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "type": raw.get("type"),
        "reason": raw.get("reason"),
    }


def _apply_lineup_and_injury_context(
    players: list[dict[str, Any]],
    lineups: dict[str, Any],
    injuries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    starters, substitutes = _lineup_role_maps(lineups)
    injuries_by_id = {str(item.get("player_id")): item for item in injuries if item.get("player_id")}
    injuries_by_name = {_norm(item.get("player_name")): item for item in injuries if item.get("player_name")}

    for player in players:
        player_id = str(player.get("player_id") or "")
        player_name = _norm(player.get("player_name"))
        player["starter"] = player_id in starters or player_name in starters
        player["substitute"] = player_id in substitutes or player_name in substitutes
        injury = injuries_by_id.get(player_id) or injuries_by_name.get(player_name)
        if injury:
            player["injured"] = True
            player["injury_reason"] = injury.get("reason") or injury.get("type")
    return players


def _lineup_role_maps(lineups: dict[str, Any]) -> tuple[set[str], set[str]]:
    starters: set[str] = set()
    substitutes: set[str] = set()
    for team in (lineups.get("teams") or {}).values():
        for player in team.get("starters") or []:
            starters.add(str(player.get("id") or ""))
            starters.add(_norm(player.get("name")))
        for player in team.get("substitutes") or []:
            substitutes.add(str(player.get("id") or ""))
            substitutes.add(_norm(player.get("name")))
    return starters, substitutes


def _lineup_player_ids(lineups: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for team in (lineups.get("teams") or {}).values():
        for player in (team.get("starters") or []) + (team.get("substitutes") or []):
            if player.get("id"):
                ids.add(str(player["id"]))
    return ids


def _lineup_player(entry: dict[str, Any]) -> dict[str, Any] | None:
    player = entry.get("player") if isinstance(entry.get("player"), dict) else {}
    if not player:
        return None
    return {
        "id": player.get("id"),
        "name": player.get("name"),
        "number": player.get("number"),
        "position": player.get("pos"),
    }


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested = value.get("response")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _unique(items: list[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique
