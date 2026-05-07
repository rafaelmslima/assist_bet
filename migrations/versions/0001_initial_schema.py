"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"])
    op.create_index("ix_users_chat_id", "users", ["chat_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

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
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
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
        "bets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(length=50), nullable=False),
        sa.Column("league", sa.String(length=100), nullable=True),
        sa.Column("fixture_name", sa.String(length=255), nullable=False),
        sa.Column("market", sa.String(length=100), nullable=False),
        sa.Column("selection", sa.String(length=255), nullable=False),
        sa.Column("odd", sa.Float(), nullable=False),
        sa.Column("stake", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=True),
        sa.Column("profit_loss", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bets_id", "bets", ["id"])
    op.create_index("ix_bets_user_id", "bets", ["user_id"])
    op.create_index("ix_bets_sport", "bets", ["sport"])
    op.create_index("ix_bets_league", "bets", ["league"])
    op.create_index("ix_bets_market", "bets", ["market"])
    op.create_index("ix_bets_status", "bets", ["status"])
    op.create_index("ix_bets_result", "bets", ["result"])

    op.create_table(
        "analysis_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("context_alerts", sa.Text(), nullable=True),
        sa.Column("suggested_markets", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_cards_id", "analysis_cards", ["id"])
    op.create_index("ix_analysis_cards_user_id", "analysis_cards", ["user_id"])
    op.create_index("ix_analysis_cards_fixture_id", "analysis_cards", ["fixture_id"])
    op.create_index("ix_analysis_cards_risk_level", "analysis_cards", ["risk_level"])

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
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_stats_snapshots_id", "player_stats_snapshots", ["id"])
    op.create_index("ix_player_stats_snapshots_player_id", "player_stats_snapshots", ["player_id"])
    op.create_index("ix_player_stats_snapshots_fixture_id", "player_stats_snapshots", ["fixture_id"])

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
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_stats_snapshots_id", "team_stats_snapshots", ["id"])
    op.create_index("ix_team_stats_snapshots_team_id", "team_stats_snapshots", ["team_id"])
    op.create_index("ix_team_stats_snapshots_fixture_id", "team_stats_snapshots", ["fixture_id"])

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


def downgrade() -> None:
    op.drop_index("ix_recommendations_market", table_name="recommendations")
    op.drop_index("ix_recommendations_sport", table_name="recommendations")
    op.drop_index("ix_recommendations_fixture_id", table_name="recommendations")
    op.drop_index("ix_recommendations_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_team_stats_snapshots_fixture_id", table_name="team_stats_snapshots")
    op.drop_index("ix_team_stats_snapshots_team_id", table_name="team_stats_snapshots")
    op.drop_index("ix_team_stats_snapshots_id", table_name="team_stats_snapshots")
    op.drop_table("team_stats_snapshots")
    op.drop_index("ix_player_stats_snapshots_fixture_id", table_name="player_stats_snapshots")
    op.drop_index("ix_player_stats_snapshots_player_id", table_name="player_stats_snapshots")
    op.drop_index("ix_player_stats_snapshots_id", table_name="player_stats_snapshots")
    op.drop_table("player_stats_snapshots")
    op.drop_index("ix_odds_snapshots_collected_at", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_selection", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_market", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_bookmaker", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_fixture_id", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_id", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_index("ix_analysis_cards_risk_level", table_name="analysis_cards")
    op.drop_index("ix_analysis_cards_fixture_id", table_name="analysis_cards")
    op.drop_index("ix_analysis_cards_user_id", table_name="analysis_cards")
    op.drop_index("ix_analysis_cards_id", table_name="analysis_cards")
    op.drop_table("analysis_cards")
    op.drop_index("ix_bets_result", table_name="bets")
    op.drop_index("ix_bets_status", table_name="bets")
    op.drop_index("ix_bets_market", table_name="bets")
    op.drop_index("ix_bets_league", table_name="bets")
    op.drop_index("ix_bets_sport", table_name="bets")
    op.drop_index("ix_bets_user_id", table_name="bets")
    op.drop_index("ix_bets_id", table_name="bets")
    op.drop_table("bets")
    op.drop_index("ix_players_name", table_name="players")
    op.drop_index("ix_players_team_id", table_name="players")
    op.drop_index("ix_players_external_id", table_name="players")
    op.drop_index("ix_players_sport", table_name="players")
    op.drop_index("ix_players_id", table_name="players")
    op.drop_table("players")
    op.drop_index("ix_fixtures_status", table_name="fixtures")
    op.drop_index("ix_fixtures_fixture_date", table_name="fixtures")
    op.drop_index("ix_fixtures_away_team_id", table_name="fixtures")
    op.drop_index("ix_fixtures_home_team_id", table_name="fixtures")
    op.drop_index("ix_fixtures_season", table_name="fixtures")
    op.drop_index("ix_fixtures_league", table_name="fixtures")
    op.drop_index("ix_fixtures_external_id", table_name="fixtures")
    op.drop_index("ix_fixtures_sport", table_name="fixtures")
    op.drop_index("ix_fixtures_id", table_name="fixtures")
    op.drop_table("fixtures")
    op.drop_index("ix_teams_league", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_index("ix_teams_external_id", table_name="teams")
    op.drop_index("ix_teams_sport", table_name="teams")
    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_chat_id", table_name="users")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
