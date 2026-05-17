"""Ensure admin user can log in.

Revision ID: 0005_ensure_admin_user
Revises: 0004_reset_admin_password
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_ensure_admin_user"
down_revision = "0004_reset_admin_password"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "rafaelmslima.miranda2@gmail.com"
PASSWORD_HASH = "$2b$12$5Jrogy/mbSB8pBUzUV6hAu7uTCHZ9u6GuzVUD5nPOKxjbhcU40Oze"


def upgrade() -> None:
    bind = op.get_bind()
    existing_id = bind.scalar(
        sa.text("SELECT id FROM web_users WHERE lower(email) = :email LIMIT 1"),
        {"email": ADMIN_EMAIL},
    )

    if existing_id is None:
        bind.execute(
            sa.text(
                """
                INSERT INTO web_users (email, password_hash, role, is_active, created_at, updated_at)
                VALUES (:email, :password_hash, 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"email": ADMIN_EMAIL, "password_hash": PASSWORD_HASH},
        )
        return

    bind.execute(
        sa.text(
            """
            UPDATE web_users
            SET password_hash = :password_hash,
                role = 'admin',
                is_active = true,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id
            """
        ),
        {"password_hash": PASSWORD_HASH, "user_id": existing_id},
    )


def downgrade() -> None:
    raise RuntimeError("Admin user bootstrap migration cannot restore the previous user state.")
