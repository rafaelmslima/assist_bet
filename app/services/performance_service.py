from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Recommendation


class PerformanceService:
    def by_market(self, db: Session) -> list[tuple[str, int]]:
        q = select(Recommendation.market, func.count(Recommendation.id)).group_by(Recommendation.market)
        return list(db.execute(q).all())
