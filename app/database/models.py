from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )


class WebUser(Base, TimestampMixin):
    __tablename__ = "web_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Team(Base, TimestampMixin):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("sport", "external_id", name="uq_teams_sport_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sport: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    league: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    players: Mapped[list[Player]] = relationship(back_populates="team")
    home_fixtures: Mapped[list[Fixture]] = relationship(
        foreign_keys="Fixture.home_team_id",
        back_populates="home_team",
    )
    away_fixtures: Mapped[list[Fixture]] = relationship(
        foreign_keys="Fixture.away_team_id",
        back_populates="away_team",
    )
    stats_snapshots: Mapped[list[TeamStatsSnapshot]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )


class Player(Base, TimestampMixin):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("sport", "external_id", name="uq_players_sport_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sport: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)

    team: Mapped[Team] = relationship(back_populates="players")
    stats_snapshots: Mapped[list[PlayerStatsSnapshot]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )


class Fixture(Base, TimestampMixin):
    __tablename__ = "fixtures"
    __table_args__ = (UniqueConstraint("sport", "external_id", name="uq_fixtures_sport_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sport: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    league: Mapped[str] = mapped_column(String(100), index=True)
    season: Mapped[str] = mapped_column(String(50), index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    fixture_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)

    home_team: Mapped[Team] = relationship(
        foreign_keys=[home_team_id],
        back_populates="home_fixtures",
    )
    away_team: Mapped[Team] = relationship(
        foreign_keys=[away_team_id],
        back_populates="away_fixtures",
    )
    team_stats_snapshots: Mapped[list[TeamStatsSnapshot]] = relationship(
        back_populates="fixture",
        cascade="all, delete-orphan",
    )
    player_stats_snapshots: Mapped[list[PlayerStatsSnapshot]] = relationship(
        back_populates="fixture",
        cascade="all, delete-orphan",
    )
    odds_snapshots: Mapped[list[OddsSnapshot]] = relationship(
        back_populates="fixture",
        cascade="all, delete-orphan",
    )


class TeamStatsSnapshot(Base):
    __tablename__ = "team_stats_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True, index=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_5_form: Mapped[str | None] = mapped_column(String(50), nullable=True)
    home_avg_scored: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_avg_conceded: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_avg_scored: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_avg_conceded: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shots: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shots_on_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_corners: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    team: Mapped[Team] = relationship(back_populates="stats_snapshots")
    fixture: Mapped[Fixture | None] = relationship(back_populates="team_stats_snapshots")


class PlayerStatsSnapshot(Base):
    __tablename__ = "player_stats_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True, index=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    avg_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_rebounds: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_assists: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shots: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shots_on_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_goals: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_tackles: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cards: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    player: Mapped[Player] = relationship(back_populates="stats_snapshots")
    fixture: Mapped[Fixture | None] = relationship(back_populates="player_stats_snapshots")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String(100), index=True)
    market: Mapped[str] = mapped_column(String(100), index=True)
    selection: Mapped[str] = mapped_column(String(255), index=True)
    odd: Mapped[float] = mapped_column(Float)
    implied_probability: Mapped[float] = mapped_column(Float)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)

    fixture: Mapped[Fixture] = relationship(back_populates="odds_snapshots")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fixture_id: Mapped[str] = mapped_column(String(100), index=True)
    sport: Mapped[str] = mapped_column(String(30), index=True)
    market: Mapped[str] = mapped_column(String(100), index=True)
    selection: Mapped[str] = mapped_column(String(255))
    score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[str] = mapped_column(String(20))
    risk: Mapped[str] = mapped_column(String(20))
    stake_suggestion: Mapped[str] = mapped_column(String(30))
    odd: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge: Mapped[float | None] = mapped_column(Float, nullable=True)
    archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    traps: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_result: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
