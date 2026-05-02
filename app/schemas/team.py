from __future__ import annotations

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    name: str
    sport: str
    league: str | None = None
    country: str | None = None
