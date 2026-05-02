from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev
from typing import Any

from app.integrations.balldontlie_client import BalldontlieClient
from app.services.nba_matchup_service import NbaMatchupService


@dataclass(frozen=True)
class NbaGamePlayerContext:
    game: dict[str, Any]
    players: list[dict[str, Any]]
    injuries: list[dict[str, Any]]
    team_context: dict[str, dict[str, Any]]
    data_quality: list[str]


class NbaPlayerService:
    """Collects NBA player data for a selected game."""

    def __init__(
        self,
        client: BalldontlieClient | None = None,
        matchup_service: NbaMatchupService | None = None,
    ) -> None:
        self.client = client or BalldontlieClient()
        self.matchup_service = matchup_service or NbaMatchupService()
        self._cache: dict[str, Any] = {}

    def build_game_player_context(self, game: dict[str, Any], season: int | None = None) -> NbaGamePlayerContext:
        season = season or current_nba_season()
        home_id = game.get("home_team_id")
        visitor_id = game.get("visitor_team_id")
        injuries = self._get_injuries()
        team_context = {
            str(home_id): self._get_team_context(home_id),
            str(visitor_id): self._get_team_context(visitor_id),
        }
        data_quality: list[str] = []

        players = []
        for team_id, opponent_id in ((home_id, visitor_id), (visitor_id, home_id)):
            if team_id in (None, ""):
                continue
            roster = self._get_roster(int(team_id))
            if not roster:
                data_quality.append(f"sem elenco retornado para team_id {team_id}")
                continue
            roster = roster[:12]
            averages = self._get_averages([int(player["player_id"]) for player in roster], season)
            recent = self._get_recent_stats([int(player["player_id"]) for player in roster], season)
            for player in roster:
                merged = {
                    **player,
                    **averages.get(str(player["player_id"]), {}),
                    "recent_games": recent.get(str(player["player_id"]), []),
                    "opponent_team_id": opponent_id,
                    "injury_status": _injury_status(player, injuries),
                }
                merged["recent_metrics"] = _recent_metrics(merged["recent_games"])
                matchup = self.matchup_service.analyze_matchup(
                    merged,
                    team_context.get(str(opponent_id), {}),
                )
                merged["matchup"] = matchup
                players.append(merged)

        if players:
            data_quality.append("usando medias de temporada e ultimos jogos da balldontlie")
        else:
            data_quality.append("sem dados suficientes de jogadores NBA")

        return NbaGamePlayerContext(
            game=game,
            players=players,
            injuries=injuries,
            team_context=team_context,
            data_quality=_unique(data_quality),
        )

    def _get_roster(self, team_id: int) -> list[dict[str, Any]]:
        cache_key = f"roster:{team_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        players: list[dict[str, Any]] = []
        cursor = None
        for _ in range(2):
            response = self.client.get_players_by_team(team_id, cursor=cursor)
            if not response.get("ok"):
                break
            players.extend(_normalize_players(response.get("data") or []))
            cursor = (response.get("meta") or {}).get("pagination", {}).get("next_cursor")
            if not cursor:
                break
        self._cache[cache_key] = players
        return players

    def _get_averages(self, player_ids: list[int], season: int) -> dict[str, dict[str, Any]]:
        cache_key = f"averages:{season}:{','.join(str(item) for item in sorted(player_ids))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        averages: dict[str, dict[str, Any]] = {}
        for chunk in _chunks(player_ids, 25):
            response = self.client.get_season_averages(chunk, season)
            if not response.get("ok"):
                continue
            for item in response.get("data") or []:
                player_id = str(item.get("player_id") or _nested_get(item, "player", "id"))
                if player_id:
                    averages[player_id] = _normalize_average(item)
        self._cache[cache_key] = averages
        return averages

    def _get_recent_stats(self, player_ids: list[int], season: int) -> dict[str, list[dict[str, Any]]]:
        cache_key = f"recent:{season}:{','.join(str(item) for item in sorted(player_ids))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        grouped: dict[str, list[dict[str, Any]]] = {}
        for chunk in _chunks(player_ids, 10):
            response = self.client.get_stats_by_players(chunk, season, per_page=100)
            if not response.get("ok"):
                continue
            for item in response.get("data") or []:
                player_id = str(_nested_get(item, "player", "id") or item.get("player_id"))
                if not player_id:
                    continue
                grouped.setdefault(player_id, []).append(_normalize_stat(item))
        for player_id, items in grouped.items():
            grouped[player_id] = items[:5]
        self._cache[cache_key] = grouped
        return grouped

    def _get_injuries(self) -> list[dict[str, Any]]:
        cache_key = "injuries"
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = self.client.get_player_injuries()
        if not response.get("ok"):
            return []
        injuries = [_normalize_injury(item) for item in response.get("data") or []]
        self._cache[cache_key] = injuries
        return injuries

    def _get_team_context(self, team_id: Any) -> dict[str, Any]:
        if team_id in (None, ""):
            return {}
        cache_key = f"team_context:{team_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = self.client.get_team_home_away_stats(int(team_id))
        if not response.get("ok"):
            return {}
        data = response.get("data")
        result = data if isinstance(data, dict) else {}
        self._cache[cache_key] = result
        return result


def current_nba_season(today: datetime | None = None) -> int:
    today = today or datetime.now()
    return today.year if today.month >= 10 else today.year - 1


def _normalize_players(raw_players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    players = []
    for item in raw_players:
        first = item.get("first_name") or ""
        last = item.get("last_name") or ""
        team = item.get("team") if isinstance(item.get("team"), dict) else {}
        players.append(
            {
                "player_id": item.get("id"),
                "player_name": f"{first} {last}".strip() or item.get("name"),
                "position": item.get("position"),
                "team_id": team.get("id") or item.get("team_id"),
                "team_name": team.get("full_name") or team.get("name"),
            }
        )
    return [player for player in players if player.get("player_id") and player.get("player_name")]


def _normalize_average(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "season_min": _to_float(item.get("min")),
        "season_pts": _to_float(item.get("pts")),
        "season_reb": _to_float(item.get("reb")),
        "season_ast": _to_float(item.get("ast")),
        "season_fg3m": _to_float(item.get("fg3m")),
    }


def _normalize_stat(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "min": _minutes(item.get("min")),
        "pts": _to_float(item.get("pts")),
        "reb": _to_float(item.get("reb")),
        "ast": _to_float(item.get("ast")),
        "fg3m": _to_float(item.get("fg3m")),
    }


def _normalize_injury(item: dict[str, Any]) -> dict[str, Any]:
    player = item.get("player") if isinstance(item.get("player"), dict) else {}
    return {
        "player_id": player.get("id") or item.get("player_id"),
        "player_name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
        "status": item.get("status") or item.get("designation"),
        "description": item.get("description") or item.get("comment"),
    }


def _recent_metrics(games: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "games": len(games),
        "min": _avg([value for value in (_to_float(item.get("min")) for item in games) if value is not None]),
        "pts": _avg([value for value in (_to_float(item.get("pts")) for item in games) if value is not None]),
        "reb": _avg([value for value in (_to_float(item.get("reb")) for item in games) if value is not None]),
        "ast": _avg([value for value in (_to_float(item.get("ast")) for item in games) if value is not None]),
        "fg3m": _avg([value for value in (_to_float(item.get("fg3m")) for item in games) if value is not None]),
        "consistency": _consistency([_to_float(item.get("pts")) or 0 for item in games]),
    }


def _injury_status(player: dict[str, Any], injuries: list[dict[str, Any]]) -> dict[str, Any] | None:
    player_id = str(player.get("player_id") or "")
    player_name = _norm(player.get("player_name"))
    for item in injuries:
        if str(item.get("player_id")) == player_id or _norm(item.get("player_name")) == player_name:
            return item
    return None


def _minutes(value: Any) -> float | None:
    if isinstance(value, str) and ":" in value:
        minutes, seconds = value.split(":", 1)
        try:
            return float(minutes) + float(seconds) / 60
        except ValueError:
            return None
    return _to_float(value)


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _avg(values: list[float]) -> float | None:
    return round(mean(values), 2) if values else None


def _consistency(values: list[float]) -> str:
    if len(values) < 3:
        return "dados insuficientes"
    avg = mean(values)
    if avg <= 0:
        return "baixa"
    coefficient = pstdev(values) / avg
    if coefficient <= 0.25:
        return "alta"
    if coefficient <= 0.5:
        return "media"
    return "baixa"


def _chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _unique(items: list[str]) -> list[str]:
    unique = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique
