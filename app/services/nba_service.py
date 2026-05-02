from __future__ import annotations

from app.integrations.balldontlie_client import BalldontlieClient


class NbaService:
    def __init__(self, client: BalldontlieClient | None = None) -> None:
        self.client = client or BalldontlieClient()

    def get_daily_games(self, date: str) -> dict:
        return self.client.get_games_by_date(date)

    def get_player_profile(self, player_id: int) -> dict:
        return self.client.get_player(player_id)
