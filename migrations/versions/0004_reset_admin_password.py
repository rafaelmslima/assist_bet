"""Reset admin password.

Revision ID: 0004_reset_admin_password
Revises: 0003_remove_telegram_legacy
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_reset_admin_password"
down_revision = "0003_remove_telegram_legacy"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "rafaelmslima.miranda2@gmail.com"
PASSWORD_HASH = "$2b$12$5Jrogy/mbSB8pBUzUV6hAu7uTCHZ9u6GuzVUD5nPOKxjbhcU40Oze"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE web_users
            SET password_hash = :password_hash
            WHERE lower(email) = :email
            """
        ),
        {"password_hash": PASSWORD_HASH, "email": ADMIN_EMAIL},
    )


def downgrade() -> None:
    raise RuntimeError("Password reset migration cannot restore the previous password hash.")
