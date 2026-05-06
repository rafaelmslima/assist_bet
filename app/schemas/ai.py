from __future__ import annotations

from pydantic import BaseModel


class AIInterpretation(BaseModel):
    text: str
    mode: str
