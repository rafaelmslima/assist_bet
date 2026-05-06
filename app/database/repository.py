from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AnalysisCard, Bet, OddsSnapshot, Recommendation, User, utc_now
from app.schemas.bet import BetCreate


def get_or_create_user(
    db: Session,
    *,
    telegram_user_id: int,
    chat_id: int,
    first_name: str | None = None,
    username: str | None = None,
) -> User:
    """Create a Telegram user or update the existing record."""
    statement = select(User).where(User.telegram_user_id == telegram_user_id)
    user = db.scalar(statement)

    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            first_name=first_name,
            username=username,
            is_active=True,
        )
        db.add(user)
    else:
        user.chat_id = chat_id
        user.first_name = first_name
        user.username = username
        user.is_active = True

    db.commit()
    db.refresh(user)
    return user


def create_bet(db: Session, payload: BetCreate) -> Bet:
    bet = Bet(**payload.model_dump())
    db.add(bet)
    db.commit()
    db.refresh(bet)
    return bet


def list_open_bets(db: Session, user_id: int, limit: int = 20) -> list[Bet]:
    statement = (
        select(Bet)
        .where(Bet.user_id == user_id, Bet.status == "open")
        .order_by(Bet.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_recent_bets(db: Session, user_id: int, limit: int = 10) -> list[Bet]:
    statement = (
        select(Bet)
        .where(Bet.user_id == user_id)
        .order_by(Bet.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_user_bets(db: Session, user_id: int, limit: int = 20) -> list[Bet]:
    return list_recent_bets(db, user_id=user_id, limit=limit)


def list_recent_settled_bets(db: Session, user_id: int, limit: int = 10) -> list[Bet]:
    statement = (
        select(Bet)
        .where(Bet.user_id == user_id, Bet.status.in_(("won", "lost", "void")))
        .order_by(Bet.settled_at.desc(), Bet.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def calculate_user_roi(db: Session, user_id: int) -> dict[str, float | int]:
    statement = select(Bet).where(Bet.user_id == user_id, Bet.status.in_(("won", "lost", "void")))
    bets = list(db.scalars(statement))
    graded_bets = [bet for bet in bets if bet.status in {"won", "lost"}]
    won_bets = [bet for bet in bets if bet.status == "won"]
    lost_bets = [bet for bet in bets if bet.status == "lost"]
    void_bets = [bet for bet in bets if bet.status == "void"]
    total_stake = sum(bet.stake for bet in graded_bets)
    profit_loss = sum(bet.profit_loss or 0 for bet in bets)
    roi = (profit_loss / total_stake) if total_stake else 0.0
    win_rate = (len(won_bets) / len(graded_bets)) if graded_bets else 0.0
    average_odd = (sum(bet.odd for bet in graded_bets) / len(graded_bets)) if graded_bets else 0.0

    return {
        "total_bets": len(bets),
        "won_bets": len(won_bets),
        "lost_bets": len(lost_bets),
        "void_bets": len(void_bets),
        "total_stake": total_stake,
        "profit_loss": profit_loss,
        "roi": roi,
        "win_rate": win_rate,
        "average_odd": average_odd,
    }


def settle_bet(
    db: Session,
    *,
    bet_id: int,
    status: str,
    user_id: int | None = None,
) -> Bet | None:
    if status not in {"won", "lost", "void"}:
        raise ValueError("Status deve ser won, lost ou void.")

    bet = db.get(Bet, bet_id)
    if bet is None:
        return None
    if user_id is not None and bet.user_id != user_id:
        return None

    bet.status = status
    bet.result = status
    bet.profit_loss = _profit_loss_for_status(bet.stake, bet.odd, status)
    bet.settled_at = utc_now()

    db.commit()
    db.refresh(bet)
    return bet


def update_bet_result(
    db: Session,
    *,
    bet_id: int,
    result: str,
    profit_loss: float | None = None,
    status: str | None = None,
    user_id: int | None = None,
) -> Bet | None:
    final_status = status or result
    if final_status not in {"won", "lost", "void"}:
        raise ValueError("Status deve ser won, lost ou void.")

    bet = db.get(Bet, bet_id)
    if bet is None:
        return None
    if user_id is not None and bet.user_id != user_id:
        return None

    bet.result = result
    bet.status = final_status
    bet.profit_loss = profit_loss if profit_loss is not None else _profit_loss_for_status(bet.stake, bet.odd, final_status)
    bet.settled_at = utc_now()

    db.commit()
    db.refresh(bet)
    return bet


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


def save_analysis_card(
    db: Session,
    *,
    user_id: int,
    fixture_id: int,
    summary: str,
    risk_level: str,
    strengths: str | None = None,
    weaknesses: str | None = None,
    context_alerts: str | None = None,
    suggested_markets: str | None = None,
) -> AnalysisCard:
    card = AnalysisCard(
        user_id=user_id,
        fixture_id=fixture_id,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        context_alerts=context_alerts,
        suggested_markets=suggested_markets,
        risk_level=risk_level,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> User | None:
    statement = select(User).where(User.telegram_user_id == telegram_user_id)
    return db.scalar(statement)


def save_model(db: Session, model_data: Any) -> Any:
    """Small helper for future repositories that persist SQLAlchemy model instances."""
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


def _profit_loss_for_status(stake: float, odd: float, status: str) -> float:
    if status == "won":
        return stake * (odd - 1)
    if status == "lost":
        return -stake
    if status == "void":
        return 0.0
    return 0.0
