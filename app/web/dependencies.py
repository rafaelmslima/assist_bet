from __future__ import annotations

from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import WebUser
from app.database.repository import get_web_user_by_id
from app.database.session import SessionLocal
from app.web.security import decode_session_token


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_web_user(
    db: Session = Depends(get_db_session),
    session_token: str | None = Cookie(default=None, alias=settings.web_session_cookie_name),
) -> WebUser:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao ausente.")

    payload = decode_session_token(session_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida.")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida.") from None

    user = get_web_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inativo ou inexistente.")
    return user
