from __future__ import annotations

from app.services.odds_service import OddsService


def run_odds_update_job(sport_key: str, event_id: str) -> dict:
    """Fetch latest odds for an event."""
    # TODO: Wire into APScheduler when scheduling is introduced.
    return OddsService().get_event_odds(sport_key=sport_key, event_id=event_id)
