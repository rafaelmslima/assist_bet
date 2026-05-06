from __future__ import annotations

from datetime import date, timedelta

from app.integrations.balldontlie_client import BalldontlieClient


class NbaDataService:
    def __init__(self, client: BalldontlieClient | None = None) -> None:
        self.client = client or BalldontlieClient()

    def games_today(self) -> list[dict]:
        return self._games_for(date.today().isoformat())

    def games_tomorrow(self) -> list[dict]:
        return self._games_for((date.today() + timedelta(days=1)).isoformat())

    def _games_for(self, day: str) -> list[dict]:
        response = self.client.get_games_by_date(day)
        if not response.get("ok"):
            return []
        out = []
        for game in response.get("data", []):
            out.append(
                {
                    "fixture_id": game.get("id"),
                    "home_team": (game.get("home_team") or {}).get("full_name"),
                    "away_team": (game.get("visitor_team") or {}).get("full_name"),
                    "league": "NBA",
                }
            )
        return out
