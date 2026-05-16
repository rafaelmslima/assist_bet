"""Add web users.

Revision ID: 0002_web_users
Revises: 0001_initial_schema
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_web_users"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_web_users_is_active", table_name="web_users")
    op.drop_index("ix_web_users_role", table_name="web_users")
    op.drop_index("ix_web_users_email", table_name="web_users")
    op.drop_index("ix_web_users_id", table_name="web_users")
    op.drop_table("web_users")
