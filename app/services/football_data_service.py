from __future__ import annotations

from datetime import date, timedelta

from app.integrations.api_football_client import ApiFootballClient


class FootballDataService:
    def __init__(self, client: ApiFootballClient | None = None) -> None:
        self.client = client or ApiFootballClient()

    def games_today(self) -> list[dict]:
        return self._fixtures_for(date.today().isoformat())

    def games_tomorrow(self) -> list[dict]:
        return self._fixtures_for((date.today() + timedelta(days=1)).isoformat())

    def _fixtures_for(self, day: str) -> list[dict]:
        response = self.client.get_fixtures_by_date(day)
        if not response.get("ok"):
            return []
        fixtures = []
        for item in response.get("data", []):
            teams = item.get("teams", {})
            fixture = item.get("fixture", {})
            league = item.get("league", {})
            fixtures.append(
                {
                    "fixture_id": fixture.get("id"),
                    "home_team": (teams.get("home") or {}).get("name"),
                    "away_team": (teams.get("away") or {}).get("name"),
                    "league": league.get("name"),
                    "league_id": league.get("id"),
                    "season": league.get("season"),
                }
            )
        return fixtures
