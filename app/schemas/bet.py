from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BetCreate(BaseModel):
    user_id: int
    sport: str
    fixture_name: str
    market: str
    selection: str
    odd: float = Field(gt=1)
    stake: float = Field(gt=0)
    league: str | None = None
    reason: str | None = None
    status: str = "open"
    result: str | None = None
    profit_loss: float | None = None


class BetRead(BetCreate):
    id: int
    created_at: datetime
    settled_at: datetime | None = None

    model_config = {"from_attributes": True}
