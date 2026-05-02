from __future__ import annotations

from pydantic import BaseModel


class Odds(BaseModel):
    event_id: str
    bookmaker: str
    market: str
    selection: str
    price: float
