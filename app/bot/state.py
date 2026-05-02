from __future__ import annotations

from dataclasses import dataclass

from app.bot.intents import UserIntent


@dataclass
class UserState:
    intent: UserIntent


_USER_STATES: dict[int, UserState] = {}


def set_user_intent(telegram_user_id: int, intent: UserIntent) -> None:
    _USER_STATES[telegram_user_id] = UserState(intent=intent)


def get_user_state(telegram_user_id: int) -> UserState | None:
    return _USER_STATES.get(telegram_user_id)


def clear_user_state(telegram_user_id: int) -> None:
    _USER_STATES.pop(telegram_user_id, None)
