from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Confidence = Literal["baixa", "media", "alta"]


class FootballProbabilityEstimate(BaseModel):
    model_config = ConfigDict(validate_default=True)

    market_key: str
    label: str
    probability_percent: int | None = Field(default=None, ge=1, le=99)
    confidence: Confidence = "baixa"
    rationale: str = ""
    data_status: Literal["estimado", "dados_insuficientes"] = "estimado"

    @field_validator("data_status")
    @classmethod
    def require_probability_when_estimated(cls, value: str, info):
        probability = info.data.get("probability_percent")
        if value == "estimado" and probability is None:
            raise ValueError("probability_percent is required when data_status is estimado")
        return value


class FootballBetSuggestion(BaseModel):
    market_key: str | None = None
    label: str = "sem entrada pre-jogo"
    min_acceptable_odd: float | None = Field(default=None, gt=1)
    has_confirmed_value: bool = False
    reason: str = ""

    @model_validator(mode="after")
    def require_min_odd_when_value_is_confirmed(self) -> "FootballBetSuggestion":
        if self.has_confirmed_value and self.min_acceptable_odd is None:
            raise ValueError("min_acceptable_odd is required when has_confirmed_value is true")
        return self


class FootballAIAnalysis(BaseModel):
    fixture_label: str
    probabilities: list[FootballProbabilityEstimate] = Field(min_length=1)
    match_reading: str
    possible_entry: FootballBetSuggestion
    avoid: str

    @field_validator("probabilities")
    @classmethod
    def require_core_markets(cls, values: list[FootballProbabilityEstimate]):
        required = {
            "over_1_5_goals",
            "over_2_5_goals",
            "home_over_0_5_goals",
            "away_over_0_5_goals",
            "favorite_win",
            "corners",
        }
        present = {item.market_key for item in values}
        missing = required - present
        if missing:
            raise ValueError(f"missing probability markets: {', '.join(sorted(missing))}")
        return values
