from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class ApiFootballClient:
    """HTTP client for API-Football data."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_host: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or settings.api_football_key
        self.base_url = base_url or settings.api_football_base_url
        self.api_host = api_host or settings.api_football_host
        if not self.api_host and "rapidapi.com" in self.base_url:
            self.api_host = "api-football-v1.p.rapidapi.com"
        self.timeout = httpx.Timeout(timeout)

    def get_team_by_name(self, team_name: str) -> dict[str, Any]:
        # TODO: Confirm exact endpoint/params against current API-Football docs.
        return self._get("/teams", {"search": team_name})

    def get_team_fixtures(
        self,
        team_id: int,
        last: int = 5,
        league_id: int | None = None,
        season: int | str | None = None,
    ) -> dict[str, Any]:
        # TODO: Confirm fixture filters for last matches by team.
        params: dict[str, Any] = {"team": team_id, "last": last}
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._get("/fixtures", params)

    def get_team_next_fixtures(
        self,
        team_id: int,
        next_games: int = 15,
        league_id: int | None = None,
        season: int | str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"team": team_id, "next": next_games, "timezone": "America/Sao_Paulo"}
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._get("/fixtures", params)

    def get_team_home_away_stats(self, team_id: int, league_id: int, season: int | str) -> dict[str, Any]:
        # TODO: Normalize home/away stats after validating API response shape.
        return self._get(
            "/teams/statistics",
            {"team": team_id, "league": league_id, "season": season},
        )

    def get_standings(self, league_id: int, season: int | str) -> dict[str, Any]:
        # TODO: Confirm standings response nesting for the selected league.
        return self._get("/standings", {"league": league_id, "season": season})

    def get_fixture_by_teams(self, home_team: str, away_team: str) -> dict[str, Any]:
        # TODO: API-Football searches fixtures by ids/date more reliably; resolve team ids first.
        return {
            "ok": True,
            "data": {"id": 101, "home_team": home_team, "away_team": away_team, "league": "Mock League"},
            "error": None,
            "meta": {"provider": "api_football", "mock": True, "home_team": home_team, "away_team": away_team},
        }

    def get_fixture_lineups(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/lineups", {"fixture": fixture_id})

    def get_fixture_statistics(self, fixture_id: int) -> dict[str, Any]:
        return self._get("/fixtures/statistics", {"fixture": fixture_id})

    def get_fixture_players(self, fixture_id: int | str, team_id: int | str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"fixture": fixture_id}
        if team_id is not None:
            params["team"] = team_id
        return self._get("/fixtures/players", params)

    def get_players(
        self,
        *,
        season: int | str,
        player_id: int | str | None = None,
        team_id: int | str | None = None,
        league_id: int | str | None = None,
        search: str | None = None,
        page: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"season": season}
        if player_id is not None:
            params["id"] = player_id
        if team_id is not None:
            params["team"] = team_id
        if league_id is not None:
            params["league"] = league_id
        if search:
            params["search"] = search
        if page is not None:
            params["page"] = page
        return self._get("/players", params)

    def get_player_stats(self, player_id: int, season: int | str) -> dict[str, Any]:
        return self.get_players(player_id=player_id, season=season)

    def get_players_by_team(self, team_id: int | str, season: int | str, league_id: int | str | None = None) -> dict[str, Any]:
        return self.get_players(team_id=team_id, season=season, league_id=league_id)

    def get_players_squad(self, team_id: int | str) -> dict[str, Any]:
        return self._get("/players/squads", {"team": team_id})

    def get_injuries(
        self,
        *,
        fixture_id: int | str | None = None,
        team_id: int | str | None = None,
        league_id: int | str | None = None,
        season: int | str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if fixture_id is not None:
            params["fixture"] = fixture_id
        if team_id is not None:
            params["team"] = team_id
        if league_id is not None:
            params["league"] = league_id
        if season is not None:
            params["season"] = season
        return self._get("/injuries", params)

    def get_sidelined(self, player_id: int | str) -> dict[str, Any]:
        return self._get("/sidelined", {"player": player_id})

    def get_predictions(self, fixture_id: int | str) -> dict[str, Any]:
        return self._get("/predictions", {"fixture": fixture_id})

    def get_league_coverage(self, league_id: int | str, season: int | str) -> dict[str, Any]:
        return self._get("/leagues", {"id": league_id, "season": season})

    def get_odds(self, fixture_id: int) -> dict[str, Any]:
        # TODO: Confirm API-Football odds plan/endpoint availability for selected bookmaker markets.
        return self._get("/odds", {"fixture": fixture_id})

    def get_fixtures_by_date(self, date: str) -> dict[str, Any]:
        # Kept for existing services.
        return self._get("/fixtures", {"date": date})

    def get_fixtures_by_league_date(self, league_id: int, date: str, season: int | str) -> dict[str, Any]:
        # TODO: Confirm timezone/date behavior against API-Football docs for each league.
        return self._get(
            "/fixtures",
            {"league": league_id, "date": date, "season": season, "timezone": "America/Sao_Paulo"},
        )

    def get_fixture_by_id(self, fixture_id: int | str) -> dict[str, Any]:
        # TODO: Expand this with lineups/statistics when the selected plan exposes them reliably.
        return self._get("/fixtures", {"id": fixture_id})

    def get_team_statistics(self, team_id: int) -> dict[str, Any]:
        # Kept for existing services; real calls should prefer get_team_home_away_stats.
        return {
            "ok": True,
            "data": {
                "team_id": team_id,
                "last_5_form": "WDLWW",
                "avg_scored": 1.6,
                "avg_conceded": 1.1,
            },
            "error": None,
            "meta": {"provider": "api_football", "mock": True, "team_id": team_id},
        }

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response(endpoint, params)

        headers = self._headers()
        try:
            with httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout) as client:
                response = client.get(endpoint.lstrip("/"), params=params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("API-Football returned HTTP status error: %s", exc.response.status_code)
            return self._http_error(exc, endpoint, params)
        except httpx.HTTPError as exc:
            logger.warning("API-Football request failed for endpoint %s: %s", endpoint, exc.__class__.__name__)
            return self._error("Falha de rede ao consultar API-Football.", endpoint, params)

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("API-Football returned non-JSON response: %s", exc)
            return self._error("Resposta inválida da API-Football.", endpoint, params)

        raw_errors = payload.get("errors")
        if raw_errors not in (None, {}, []):
            return self._error(_sanitize_api_error(raw_errors), endpoint, params)

        return {
            "ok": True,
            "data": payload.get("response", payload),
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "api_football",
                "raw_errors": raw_errors,
                "results": payload.get("results"),
                "paging": payload.get("paging") or {},
            },
        }

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}

        headers = {
            "x-apisports-key": self.api_key,
            "x-rapidapi-key": self.api_key,
        }
        if self.api_host:
            headers["x-rapidapi-host"] = self.api_host
        return headers

    @staticmethod
    def _error(error: str, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "error": error,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "api_football",
            },
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
            detail = _sanitize_api_error(payload.get("errors") or payload.get("message") or payload)
        except ValueError:
            detail = exc.response.text[:240]

        message = f"HTTP {exc.response.status_code}"
        if detail:
            message = f"{message}: {detail}"
        return ApiFootballClient._error(message, endpoint, params)

    @staticmethod
    def _mock_response(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        mock_data: list[dict[str, Any]] | dict[str, Any]
        if endpoint == "/teams":
            mock_data = [{"id": 1, "name": params.get("search", "Mock FC") if params else "Mock FC"}]
        elif endpoint == "/fixtures":
            mock_data = ApiFootballClient._mock_fixtures(params or {})
        elif endpoint == "/teams/statistics":
            team_id = int((params or {}).get("team", 1))
            mock_data = ApiFootballClient._mock_team_statistics(team_id)
        elif endpoint == "/fixtures/players":
            mock_data = []
        elif endpoint == "/players":
            mock_data = []
        elif endpoint == "/players/squads":
            mock_data = []
        elif endpoint == "/fixtures/lineups":
            mock_data = []
        elif endpoint == "/injuries":
            mock_data = []
        elif endpoint == "/predictions":
            mock_data = []
        elif endpoint == "/leagues":
            mock_data = []
        else:
            mock_data = {"message": "mock data for MVP 1"}

        return {
            "ok": True,
            "data": mock_data,
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "api_football",
                "mock": True,
                "todo": "Configure API_FOOTBALL_KEY and adjust endpoint parsing against official docs.",
            },
        }

    @staticmethod
    def _mock_fixtures(params: dict[str, Any]) -> list[dict[str, Any]]:
        league_id = int(params.get("league") or 39)
        league_names = {
            39: "Premier League",
            140: "La Liga",
            135: "Serie A",
            78: "Bundesliga",
            61: "Ligue 1",
            2: "Champions League",
            3: "Europa League",
            11: "Copa Sul-Americana",
            13: "Libertadores",
            71: "Brasileirao",
            88: "Eredivisie",
        }
        league_name = league_names.get(league_id, "Mock League")
        fixture_date = str(params.get("date") or "2026-05-01")
        fixtures = [
            ApiFootballClient._mock_fixture(
                fixture_id=101,
                league_id=league_id,
                league_name=league_name,
                fixture_date=fixture_date,
                home_id=1,
                home_name="Arsenal",
                away_id=2,
                away_name="Chelsea",
            ),
            ApiFootballClient._mock_fixture(
                fixture_id=102,
                league_id=league_id,
                league_name=league_name,
                fixture_date=fixture_date,
                home_id=3,
                home_name="Real Madrid",
                away_id=4,
                away_name="Barcelona",
            ),
        ]
        fixture_id = params.get("id")
        if fixture_id is None:
            return fixtures
        return [fixture for fixture in fixtures if str(fixture["fixture"]["id"]) == str(fixture_id)] or fixtures[:1]

    @staticmethod
    def _mock_fixture(
        fixture_id: int,
        league_id: int,
        league_name: str,
        fixture_date: str,
        home_id: int,
        home_name: str,
        away_id: int,
        away_name: str,
    ) -> dict[str, Any]:
        return {
            "fixture": {"id": fixture_id, "date": f"{fixture_date}T19:00:00+00:00", "status": {"short": "NS"}},
            "league": {"id": league_id, "name": league_name, "season": 2025},
            "teams": {
                "home": {"id": home_id, "name": home_name},
                "away": {"id": away_id, "name": away_name},
            },
            "goals": {"home": None, "away": None},
        }

    @staticmethod
    def _mock_team_statistics(team_id: int) -> dict[str, Any]:
        form_by_team = {1: "WWDLW", 2: "LDWWW", 3: "WWWLW", 4: "DWWLW"}
        return {
            "form": form_by_team.get(team_id, "WDLWW"),
            "goals": {
                "for": {"average": {"home": "1.80", "away": "1.35", "total": "1.57"}},
                "against": {"average": {"home": "0.90", "away": "1.20", "total": "1.05"}},
            },
            "fixtures": {"played": {"home": 10, "away": 10, "total": 20}},
        }


def _sanitize_api_error(error: Any) -> str:
    if error in (None, "", [], {}):
        return "Erro não especificado pela API-Football."
    if isinstance(error, dict):
        parts = []
        for key, value in error.items():
            text = str(value)
            if "key" in key.lower() or "token" in key.lower():
                text = "credencial rejeitada"
            parts.append(f"{key}: {text}")
        return "; ".join(parts)
    return str(error)
