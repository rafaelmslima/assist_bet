from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

import bcrypt
import jwt

from app.config import settings


ALGORITHM = "HS256"


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max(1, max_attempts)
        self.window_seconds = max(1, window_seconds)
        self._failures: dict[str, list[float]] = {}

    def is_limited(self, key: str) -> bool:
        attempts = self._active_attempts(key)
        return len(attempts) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        attempts = self._active_attempts(key)
        attempts.append(monotonic())
        self._failures[key] = attempts

    def record_success(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()

    def _active_attempts(self, key: str) -> list[float]:
        threshold = monotonic() - self.window_seconds
        attempts = [item for item in self._failures.get(key, []) if item >= threshold]
        self._failures[key] = attempts
        return attempts


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session_token(user_id: int, email: str, role: str) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.web_session_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.web_secret_key, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.web_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload if isinstance(payload, dict) else None
