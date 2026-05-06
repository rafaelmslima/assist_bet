from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversationState:
    sport_menu: str | None = None
