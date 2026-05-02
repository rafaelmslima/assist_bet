from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.repository import (
    calculate_user_roi,
    create_bet,
    list_open_bets,
    list_recent_bets,
    list_recent_settled_bets,
    settle_bet,
)
from app.schemas.bet import BetCreate


class BettingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def track_bet(self, payload: BetCreate):
        return create_bet(self.db, payload)

    def create_bet(self, payload: BetCreate):
        return create_bet(self.db, payload)

    def list_open_bets(self, user_id: int, limit: int = 20):
        return list_open_bets(self.db, user_id=user_id, limit=limit)

    def list_recent_bets(self, user_id: int, limit: int = 10):
        return list_recent_bets(self.db, user_id=user_id, limit=limit)

    def list_recent_settled_bets(self, user_id: int, limit: int = 10):
        return list_recent_settled_bets(self.db, user_id=user_id, limit=limit)

    def calculate_user_roi(self, user_id: int):
        return calculate_user_roi(self.db, user_id=user_id)

    def settle_bet(self, bet_id: int, user_id: int, status: str):
        return settle_bet(self.db, bet_id=bet_id, user_id=user_id, status=status)
