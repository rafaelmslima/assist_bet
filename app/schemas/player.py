from __future__ import annotations

from pydantic import BaseModel


class Player(BaseModel):
    id: int
    name: str
    team_id: int | None = None
    position: str | None = None
    sport: str
