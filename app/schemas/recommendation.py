from __future__ import annotations

from pydantic import BaseModel, Field


class MarketRecommendation(BaseModel):
    market: str
    selection: str
    score: int = Field(ge=0, le=100)
    confidence: str
    risk: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    min_acceptable_odd: float | None = None
    available_odd: float | None = None
    has_value: bool | None = None


class DecisionRecommendation(BaseModel):
    fixture: dict
    sport: str
    archetype: dict
    main_recommendation: dict
    alternative_recommendations: list[dict]
    avoid_markets: list[dict]
    traps: list[str]
    confidence: str
    risk: str
    stake_suggestion: str
    should_bet_pre_match: bool
    should_wait_live: bool
    data_quality: str
    final_verdict: str
    raw_signals: dict
