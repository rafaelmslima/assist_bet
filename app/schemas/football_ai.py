from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Confidence = Literal["baixa", "media", "alta"]
TrafficLight = Literal["vermelha", "amarela", "verde"]


class ExpectedScript(BaseModel):
    start: str = ""
    middle: str = ""
    if_early_goal: str = ""
    if_level_at_halftime: str = ""


class TacticalMatchup(BaseModel):
    title: str = "Matchup principal"
    reading: str = ""


class BettingIdea(BaseModel):
    market: str = "mercado qualitativo"
    idea: str = ""
    projection: str = ""
    projection_analysis: str = ""
    confidence: Confidence = "baixa"
    reason: str = ""


class AvoidMarket(BaseModel):
    market: str = "mercado a evitar"
    reason: str = ""


class MarketAssessment(BaseModel):
    market: str = ""
    score: int = 0
    confidence: str = ""
    reading: str = ""
    risk: str = ""
    value_note: str = ""


class OverallConfidence(BaseModel):
    level: TrafficLight = "amarela"
    reason: str = ""


class FootballAIAnalysis(BaseModel):
    model_config = ConfigDict(validate_default=True)

    fixture_label: str
    general_idea: str
    expected_script: ExpectedScript = Field(default_factory=ExpectedScript)
    tactical_matchups: list[TacticalMatchup] = Field(default_factory=list)
    motivation_context: str = ""
    recent_form_read: str = ""
    key_risks: list[str] = Field(default_factory=list)
    data_quality_read: str = ""
    team_profiles_read: list[str] = Field(default_factory=list)
    market_assessments: list[MarketAssessment] = Field(default_factory=list)
    betting_ideas: list[BettingIdea] = Field(default_factory=list)
    avoid: list[AvoidMarket] = Field(default_factory=list)
    confidence: OverallConfidence = Field(default_factory=OverallConfidence)
    checklist_before_bet: list[str] = Field(default_factory=list)
    data_quality_notes: list[str] = Field(default_factory=list)

    @field_validator("general_idea")
    @classmethod
    def require_general_idea(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("general_idea is required")
        return value

    @field_validator("betting_ideas")
    @classmethod
    def limit_betting_ideas(cls, values: list[BettingIdea]) -> list[BettingIdea]:
        return values[:5]
