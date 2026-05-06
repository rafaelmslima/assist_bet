from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisSignals(BaseModel):
    form_signal: int = Field(default=50, ge=0, le=100)
    home_away_signal: int = Field(default=50, ge=0, le=100)
    attack_signal: int = Field(default=50, ge=0, le=100)
    defense_signal: int = Field(default=50, ge=0, le=100)
    goals_trend_signal: int = Field(default=50, ge=0, le=100)
    btts_signal: int = Field(default=50, ge=0, le=100)
    under_signal: int = Field(default=50, ge=0, le=100)
    shots_signal: int = Field(default=50, ge=0, le=100)
    corners_signal: int = Field(default=50, ge=0, le=100)
    cards_signal: int = Field(default=50, ge=0, le=100)
    consistency_signal: int = Field(default=50, ge=0, le=100)
    data_quality: str = "média"
