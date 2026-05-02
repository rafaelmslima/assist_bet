from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Fixture(BaseModel):
    id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    starts_at: datetime
    status: str | None = None
