"""Remove Telegram legacy tables.

Irreversible by design: the dashboard product no longer owns the removed
Telegram tables, so rollback should restore a database backup instead of
recreating stale bot-era data structures.

Revision ID: 0003_remove_telegram_legacy
Revises: 0002_web_users
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op


revision = "0003_remove_telegram_legacy"
down_revision = "0002_web_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_chat_id", table_name="users")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")


def downgrade() -> None:
    raise RuntimeError("Irreversible migration. Restore a pre-upgrade backup to recover Telegram legacy tables.")
