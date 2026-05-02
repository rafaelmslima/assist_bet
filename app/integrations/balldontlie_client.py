from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class BalldontlieClient:
    """HTTP client for balldontlie NBA data."""

    BASE_URL = "https://api.balldontlie.io"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.api_key = settings.balldontlie_key if api_key is None else api_key
        self.timeout = httpx.Timeout(timeout)

    def get_team_by_name(self, team_name: str) -> dict[str, Any]:
        return self._get("/v1/teams", {"search": team_name})

    def get_team_games(self, team_id: int, last: int = 5, season: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"team_ids[]": team_id, "per_page": last}
        if season is not None:
            params["seasons[]"] = season
        return self._get("/v1/games", params)

    def get_team_home_away_stats(self, team_id: int) -> dict[str, Any]:
        games = self.get_team_games(team_id, last=20)
        if not games.get("ok"):
            return games
        return {
            "ok": True,
            "data": _aggregate_team_games(games.get("data") or [], team_id),
            "error": None,
            "meta": games.get("meta"),
        }

    def get_players_by_team(self, team_id: int, cursor: int | str | None = None, per_page: int = 100) -> dict[str, Any]:
        params: dict[str, Any] = {"team_ids[]": team_id, "per_page": per_page}
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/v1/players", params)

    def get_player_stats(
        self,
        player_id: int,
        season: int | None = None,
        per_page: int = 25,
        cursor: int | str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"player_ids[]": player_id, "per_page": per_page}
        if season is not None:
            params["seasons[]"] = season
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/v1/stats", params)

    def get_stats_by_players(
        self,
        player_ids: list[int],
        season: int,
        per_page: int = 100,
        cursor: int | str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"player_ids[]": player_ids, "seasons[]": season, "per_page": per_page}
        if cursor is not None:
            params["cursor"] = cursor
        return self._get("/v1/stats", params)

    def get_season_averages(
        self,
        player_ids: list[int],
        season: int,
        category: str = "general",
        average_type: str = "base",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "season": season,
            "season_type": "regular",
            "type": average_type,
            "player_ids[]": player_ids,
        }
        return self._get(f"/nba/v1/season_averages/{category}", params)

    def get_player_injuries(self) -> dict[str, Any]:
        return self._get("/v1/player_injuries")

    def get_games_today(self) -> dict[str, Any]:
        today = date.today().isoformat()
        return self.get_games_by_date(today)

    def get_game_by_teams(self, home_team: str, away_team: str) -> dict[str, Any]:
        return {
            "ok": True,
            "data": {"id": 201, "home_team": home_team, "away_team": away_team},
            "error": None,
            "meta": {"provider": "balldontlie", "mock": True, "home_team": home_team, "away_team": away_team},
        }

    def get_games_by_date(self, game_date: str) -> dict[str, Any]:
        return self._get("/v1/games", {"dates[]": game_date, "per_page": 100})

    def get_game(self, game_id: int | str) -> dict[str, Any]:
        return self._get(f"/v1/games/{game_id}")

    def get_player(self, player_id: int) -> dict[str, Any]:
        return self._get(f"/v1/players/{player_id}")

    def get_team(self, team_id: int) -> dict[str, Any]:
        return self._get(f"/v1/teams/{team_id}")

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response(endpoint, params)

        headers = {"Authorization": self.api_key}
        try:
            with httpx.Client(base_url=self.BASE_URL, headers=headers, timeout=self.timeout) as client:
                response = client.get(endpoint, params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("balldontlie returned HTTP status error: %s", exc.response.status_code)
            return self._http_error(exc, endpoint, params)
        except httpx.HTTPError as exc:
            logger.warning("balldontlie request failed for endpoint %s: %s", endpoint, exc.__class__.__name__)
            return self._error("Falha de rede ao consultar balldontlie.", endpoint, params)

        try:
            payload = response.json()
        except ValueError:
            return self._error("Resposta inválida da balldontlie.", endpoint, params)

        return {
            "ok": True,
            "data": payload.get("data", payload),
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "balldontlie",
                "pagination": payload.get("meta") or {},
            },
        }

    @staticmethod
    def _error(error: str, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "error": error,
            "meta": {"endpoint": endpoint, "params": params or {}, "provider": "balldontlie"},
        }

    @staticmethod
    def _http_error(
        exc: httpx.HTTPStatusError,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        detail = ""
        try:
            payload = exc.response.json()
            detail = str(payload.get("message") or payload)
        except ValueError:
            detail = exc.response.text[:240]
        hint = ""
        if exc.response.status_code == 401:
            hint = " Verifique se a trial/assinatura está ativa para NBA e se BALLDONTLIE_KEY é a chave do produto correto."
        elif exc.response.status_code == 429:
            hint = " Limite de requisições atingido; aguarde alguns minutos ou reduza os testes em sequência."
        return BalldontlieClient._error(f"HTTP {exc.response.status_code}: {detail}{hint}", endpoint, params)

    @staticmethod
    def _mock_response(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        if endpoint.endswith("/teams"):
            mock_data: Any = [{"id": 14, "full_name": params.get("search", "Los Angeles Lakers"), "abbreviation": "LAL"}]
        elif endpoint.endswith("/games") or "/games/" in endpoint:
            mock_data = _mock_games()
            if "/games/" in endpoint:
                game_id = endpoint.rsplit("/", 1)[-1]
                mock_data = next((game for game in mock_data if str(game["id"]) == str(game_id)), mock_data[0])
        elif endpoint.endswith("/players"):
            team_id = int(params.get("team_ids[]") or 14)
            mock_data = _mock_players(team_id)
        elif endpoint.endswith("/stats"):
            player_ids = params.get("player_ids[]")
            if isinstance(player_ids, list):
                mock_data = [item for player_id in player_ids for item in _mock_stats(int(player_id))]
            else:
                mock_data = _mock_stats(int(player_ids or 237))
        elif "/season_averages/" in endpoint:
            player_ids = params.get("player_ids[]") or []
            mock_data = [_mock_average(int(player_id)) for player_id in player_ids]
        elif endpoint.endswith("/player_injuries"):
            mock_data = []
        else:
            mock_data = {"message": "mock data for NBA MVP"}

        return {
            "ok": True,
            "data": mock_data,
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params,
                "provider": "balldontlie",
                "mock": True,
                "pagination": {},
            },
        }


def _aggregate_team_games(games: list[dict[str, Any]], team_id: int) -> dict[str, Any]:
    points_for = []
    points_against = []
    totals = []
    for game in games:
        home = _team(game, "home_team")
        visitor = _team(game, "visitor_team")
        home_score = _to_float(game.get("home_team_score"))
        visitor_score = _to_float(game.get("visitor_team_score"))
        if home_score is None or visitor_score is None:
            continue
        if str(home.get("id")) == str(team_id):
            points_for.append(home_score)
            points_against.append(visitor_score)
        elif str(visitor.get("id")) == str(team_id):
            points_for.append(visitor_score)
            points_against.append(home_score)
        totals.append(home_score + visitor_score)
    return {
        "team_id": team_id,
        "points_for_avg": _avg(points_for),
        "points_against_avg": _avg(points_against),
        "game_total_avg": _avg(totals),
    }


def _mock_games() -> list[dict[str, Any]]:
    return [
        {
            "id": 201,
            "date": "2026-05-01",
            "status": "Scheduled",
            "home_team": {"id": 14, "full_name": "Los Angeles Lakers", "abbreviation": "LAL"},
            "visitor_team": {"id": 2, "full_name": "Boston Celtics", "abbreviation": "BOS"},
            "home_team_score": 0,
            "visitor_team_score": 0,
        },
        {
            "id": 202,
            "date": "2026-05-01",
            "status": "Scheduled",
            "home_team": {"id": 10, "full_name": "Golden State Warriors", "abbreviation": "GSW"},
            "visitor_team": {"id": 8, "full_name": "Denver Nuggets", "abbreviation": "DEN"},
            "home_team_score": 0,
            "visitor_team_score": 0,
        },
    ]


def _mock_players(team_id: int) -> list[dict[str, Any]]:
    names = {
        14: [("LeBron", "James", "F"), ("Anthony", "Davis", "F-C"), ("Austin", "Reaves", "G")],
        2: [("Jayson", "Tatum", "F"), ("Jaylen", "Brown", "G-F"), ("Derrick", "White", "G")],
        10: [("Stephen", "Curry", "G"), ("Jimmy", "Butler", "F"), ("Draymond", "Green", "F")],
        8: [("Nikola", "Jokic", "C"), ("Jamal", "Murray", "G"), ("Aaron", "Gordon", "F")],
    }
    return [
        {"id": team_id * 100 + index, "first_name": first, "last_name": last, "position": position, "team": {"id": team_id}}
        for index, (first, last, position) in enumerate(names.get(team_id, names[14]), start=1)
    ]


def _mock_stats(player_id: int) -> list[dict[str, Any]]:
    base = (player_id % 10) + 14
    return [
        {
            "player": {"id": player_id, "first_name": "Mock", "last_name": f"Player {player_id}", "position": "G"},
            "min": str(29 + (index % 5)),
            "pts": base + index,
            "reb": 4 + (index % 4),
            "ast": 3 + (index % 5),
            "fg3m": 2 + (index % 3),
        }
        for index in range(5)
    ]


def _mock_average(player_id: int) -> dict[str, Any]:
    base = (player_id % 10) + 14
    return {
        "player_id": player_id,
        "min": 31.2,
        "pts": float(base + 3),
        "reb": 6.1,
        "ast": 4.8,
        "fg3m": 2.4,
    }


def _team(game: dict[str, Any], key: str) -> dict[str, Any]:
    value = game.get(key)
    return value if isinstance(value, dict) else {}


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None
