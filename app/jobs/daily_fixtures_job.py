from __future__ import annotations

from app.services.football_service import FootballService
from app.services.nba_service import NbaService


def run_daily_fixtures_job(date: str) -> dict:
    """Collect daily football fixtures and NBA games."""
    # TODO: Wire into APScheduler when scheduling is introduced.
    football_fixtures = FootballService().get_daily_fixtures(date)
    nba_games = NbaService().get_daily_games(date)

    return {
        "football": football_fixtures,
        "nba": nba_games,
    }
