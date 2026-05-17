from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import OddsSnapshot, Recommendation, WebUser, utc_now


def get_web_user_by_email(db: Session, email: str) -> WebUser | None:
    normalized_email = email.lower().strip()
    statement = select(WebUser).where(sa.func.lower(sa.func.trim(WebUser.email)) == normalized_email)
    return db.scalar(statement)


def get_web_user_by_id(db: Session, user_id: int) -> WebUser | None:
    return db.get(WebUser, user_id)


def list_web_users(db: Session) -> list[WebUser]:
    statement = select(WebUser).order_by(WebUser.role, WebUser.email)
    return list(db.scalars(statement))


def create_web_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    role: str = "admin",
    is_active: bool = True,
) -> WebUser:
    user = WebUser(
        email=email.lower().strip(),
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_web_user_password(db: Session, user: WebUser, password_hash: str) -> WebUser:
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user


def save_odds_snapshot(
    db: Session,
    *,
    fixture_id: int,
    bookmaker: str,
    market: str,
    selection: str,
    odd: float,
    implied_probability: float,
    collected_at: datetime | None = None,
) -> OddsSnapshot:
    snapshot = OddsSnapshot(
        fixture_id=fixture_id,
        bookmaker=bookmaker,
        market=market,
        selection=selection,
        odd=odd,
        implied_probability=implied_probability,
        collected_at=collected_at or utc_now(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_model(db: Session, model_data: Any) -> Any:
    db.add(model_data)
    db.commit()
    db.refresh(model_data)
    return model_data


def create_recommendation(
    db: Session,
    *,
    fixture_id: str,
    sport: str,
    market: str,
    selection: str,
    score: int,
    confidence: str,
    risk: str,
    stake_suggestion: str,
    odd: float | None = None,
    edge: float | None = None,
    archetype: str | None = None,
    traps: str | None = None,
) -> Recommendation:
    rec = Recommendation(
        fixture_id=fixture_id,
        sport=sport,
        market=market,
        selection=selection,
        score=score,
        confidence=confidence,
        risk=risk,
        stake_suggestion=stake_suggestion,
        odd=odd,
        edge=edge,
        archetype=archetype,
        traps=traps,
    )
    return save_model(db, rec)
