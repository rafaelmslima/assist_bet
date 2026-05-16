from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class WebUserRead(BaseModel):
    id: int
    email: str
    role: str


class LeagueRead(BaseModel):
    key: str
    label: str
    league_id: int
    season: int


class FixtureRead(BaseModel):
    fixture_id: int | str
    league_id: int | None = None
    league: str | None = None
    round: str | None = None
    season: int | str | None = None
    fixture_date: str | None = None
    status: str | None = None
    home_team_id: int | str | None = None
    away_team_id: int | str | None = None
    home_team: str | None = None
    away_team: str | None = None
    quick_read: list[str] | None = None


class FixtureListResponse(BaseModel):
    ok: bool
    date: str
    league: LeagueRead | None = None
    fixtures: list[FixtureRead]
    error: str | None = None


class FixtureAnalysisResponse(BaseModel):
    fixture: dict[str, Any]
    advisor_text: str
    analysis_mode: str
    analysis: dict[str, Any]
    advice: dict[str, Any]
    dossier: dict[str, Any]
    card_text: str
    player_advice_text: str
    injuries_text: str


class TextPanelResponse(BaseModel):
    fixture_id: str
    text: str
    payload: dict[str, Any] | None = None


class StatusResponse(BaseModel):
    environment: str
    database: str
    api_football_configured: bool
    openai_configured: bool
    cache: dict[str, Any]
    product: str = "dashboard de analise de jogos de futebol"
