"""Reset application schema and recreate admin user.

Revision ID: 0006_reset_postgres_schema
Revises: 0005_ensure_admin_user
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_reset_postgres_schema"
down_revision = "0005_ensure_admin_user"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "rafaelmslima.miranda2@gmail.com"
PASSWORD_HASH = "$2b$12$5Jrogy/mbSB8pBUzUV6hAu7uTCHZ9u6GuzVUD5nPOKxjbhcU40Oze"


def upgrade() -> None:
    _drop_application_tables()
    _create_current_schema()
    _create_admin_user()


def downgrade() -> None:
    raise RuntimeError("Database reset migration is destructive and cannot be downgraded.")


def _drop_application_tables() -> None:
    bind = op.get_bind()
    cascade = " CASCADE" if bind.dialect.name == "postgresql" else ""
    tables = [
        "recommendations",
        "odds_snapshots",
        "player_stats_snapshots",
        "team_stats_snapshots",
        "fixtures",
        "players",
        "teams",
        "web_users",
        "analysis_cards",
        "bets",
        "users",
    ]
    for table in tables:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{table}"{cascade}'))


def _create_current_schema() -> None:
    op.create_table(
        "web_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_web_users_id", "web_users", ["id"])
    op.create_index("ix_web_users_email", "web_users", ["email"])
    op.create_index("ix_web_users_role", "web_users", ["role"])
    op.create_index("ix_web_users_is_active", "web_users", ["is_active"])

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("league", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport", "external_id", name="uq_teams_sport_external_id"),
    )
    op.create_index("ix_teams_id", "teams", ["id"])
    op.create_index("ix_teams_sport", "teams", ["sport"])
    op.create_index("ix_teams_external_id", "teams", ["external_id"])
    op.create_index("ix_teams_name", "teams", ["name"])
    op.create_index("ix_teams_league", "teams", ["league"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport", "external_id", name="uq_players_sport_external_id"),
    )
    op.create_index("ix_players_id", "players", ["id"])
    op.create_index("ix_players_sport", "players", ["sport"])
    op.create_index("ix_players_external_id", "players", ["external_id"])
    op.create_index("ix_players_team_id", "players", ["team_id"])
    op.create_index("ix_players_name", "players", ["name"])

    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("league", sa.String(length=100), nullable=False),
        sa.Column("season", sa.String(length=50), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("fixture_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport", "external_id", name="uq_fixtures_sport_external_id"),
    )
    op.create_index("ix_fixtures_id", "fixtures", ["id"])
    op.create_index("ix_fixtures_sport", "fixtures", ["sport"])
    op.create_index("ix_fixtures_external_id", "fixtures", ["external_id"])
    op.create_index("ix_fixtures_league", "fixtures", ["league"])
    op.create_index("ix_fixtures_season", "fixtures", ["season"])
    op.create_index("ix_fixtures_home_team_id", "fixtures", ["home_team_id"])
    op.create_index("ix_fixtures_away_team_id", "fixtures", ["away_team_id"])
    op.create_index("ix_fixtures_fixture_date", "fixtures", ["fixture_date"])
    op.create_index("ix_fixtures_status", "fixtures", ["status"])

    op.create_table(
        "team_stats_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("last_5_form", sa.String(length=50), nullable=True),
        sa.Column("home_avg_scored", sa.Float(), nullable=True),
        sa.Column("home_avg_conceded", sa.Float(), nullable=True),
        sa.Column("away_avg_scored", sa.Float(), nullable=True),
        sa.Column("away_avg_conceded", sa.Float(), nullable=True),
        sa.Column("avg_shots", sa.Float(), nullable=True),
        sa.Column("avg_shots_on_target", sa.Float(), nullable=True),
        sa.Column("avg_corners", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_stats_snapshots_id", "team_stats_snapshots", ["id"])
    op.create_index("ix_team_stats_snapshots_team_id", "team_stats_snapshots", ["team_id"])
    op.create_index("ix_team_stats_snapshots_fixture_id", "team_stats_snapshots", ["fixture_id"])

    op.create_table(
        "player_stats_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("avg_minutes", sa.Float(), nullable=True),
        sa.Column("avg_points", sa.Float(), nullable=True),
        sa.Column("avg_rebounds", sa.Float(), nullable=True),
        sa.Column("avg_assists", sa.Float(), nullable=True),
        sa.Column("avg_shots", sa.Float(), nullable=True),
        sa.Column("avg_shots_on_target", sa.Float(), nullable=True),
        sa.Column("avg_goals", sa.Float(), nullable=True),
        sa.Column("avg_tackles", sa.Float(), nullable=True),
        sa.Column("avg_cards", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_stats_snapshots_id", "player_stats_snapshots", ["id"])
    op.create_index("ix_player_stats_snapshots_player_id", "player_stats_snapshots", ["player_id"])
    op.create_index("ix_player_stats_snapshots_fixture_id", "player_stats_snapshots", ["fixture_id"])

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker", sa.String(length=100), nullable=False),
        sa.Column("market", sa.String(length=100), nullable=False),
        sa.Column("selection", sa.String(length=255), nullable=False),
        sa.Column("odd", sa.Float(), nullable=False),
        sa.Column("implied_probability", sa.Float(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_odds_snapshots_id", "odds_snapshots", ["id"])
    op.create_index("ix_odds_snapshots_fixture_id", "odds_snapshots", ["fixture_id"])
    op.create_index("ix_odds_snapshots_bookmaker", "odds_snapshots", ["bookmaker"])
    op.create_index("ix_odds_snapshots_market", "odds_snapshots", ["market"])
    op.create_index("ix_odds_snapshots_selection", "odds_snapshots", ["selection"])
    op.create_index("ix_odds_snapshots_collected_at", "odds_snapshots", ["collected_at"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.String(length=100), nullable=False),
        sa.Column("sport", sa.String(length=30), nullable=False),
        sa.Column("market", sa.String(length=100), nullable=False),
        sa.Column("selection", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("stake_suggestion", sa.String(length=30), nullable=False),
        sa.Column("odd", sa.Float(), nullable=True),
        sa.Column("edge", sa.Float(), nullable=True),
        sa.Column("archetype", sa.String(length=100), nullable=True),
        sa.Column("traps", sa.Text(), nullable=True),
        sa.Column("final_result", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_id", "recommendations", ["id"])
    op.create_index("ix_recommendations_fixture_id", "recommendations", ["fixture_id"])
    op.create_index("ix_recommendations_sport", "recommendations", ["sport"])
    op.create_index("ix_recommendations_market", "recommendations", ["market"])


def _create_admin_user() -> None:
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO web_users (email, password_hash, role, is_active, created_at, updated_at)
            VALUES (:email, :password_hash, 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {"email": ADMIN_EMAIL, "password_hash": PASSWORD_HASH},
    )
