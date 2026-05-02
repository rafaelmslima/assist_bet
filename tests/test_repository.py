from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base
from app.database.repository import create_bet, get_or_create_user, update_bet_result
from app.schemas.bet import BetCreate


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine, future=True)

    def test_update_bet_result_respects_user_owner_when_provided(self) -> None:
        with self.Session() as db:
            owner = get_or_create_user(db, telegram_user_id=1, chat_id=1)
            other = get_or_create_user(db, telegram_user_id=2, chat_id=2)
            bet = create_bet(
                db,
                BetCreate(
                    user_id=owner.id,
                    sport="football",
                    league="Premier League",
                    fixture_name="Arsenal x Chelsea",
                    market="over gols",
                    selection="over 1.5",
                    odd=1.8,
                    stake=100,
                ),
            )

            denied = update_bet_result(db, bet_id=bet.id, result="won", user_id=other.id)
            allowed = update_bet_result(db, bet_id=bet.id, result="won", user_id=owner.id)

            self.assertIsNone(denied)
            self.assertIsNotNone(allowed)
            self.assertEqual(allowed.status, "won")


if __name__ == "__main__":
    unittest.main()
