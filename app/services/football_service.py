from __future__ import annotations

from app.integrations.api_football_client import ApiFootballClient


class FootballService:
    def __init__(self, client: ApiFootballClient | None = None) -> None:
        self.client = client or ApiFootballClient()

    def get_daily_fixtures(self, date: str) -> dict:
        return self.client.get_fixtures_by_date(date)

    def get_team_context(self, team_id: int) -> dict:
        return self.client.get_team_statistics(team_id)
