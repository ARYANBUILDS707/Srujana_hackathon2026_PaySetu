"""email verification

Revision ID: 5c2e8a41f0b7
Revises: d71bd50903a9
Create Date: 2026-10-25 14:00:00.000000+00:00

Hand-reviewed (Phase 7A). Adds `users.email_verified_at` and `email_verification_tokens`.

Existing users are NOT marked verified: the new column is nullable and left NULL for every
existing row, so each existing account must prove control of its inbox once (sign in, then
use the emailed link). No existing row in any table is changed; no session is revoked.
On SQLite the column is added with `ALTER TABLE ... ADD COLUMN`, so `users` (referenced by
`sessions`, `suppliers` and `password_reset_tokens`) is never rebuilt.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c2e8a41f0b7"
down_revision: str | Sequence[str] | None = "d71bd50903a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        op.execute("ALTER TABLE users ADD COLUMN email_verified_at VARCHAR(32)")
    else:
        op.add_column("users", sa.Column("email_verified_at", sa.String(length=32)))
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.String(length=32), nullable=False),
        sa.Column("used_at", sa.String(length=32), nullable=True),
        sa.Column("revoked_at", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_verification_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verification_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_email_verification_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_email_verification_tokens_user_id"), "email_verification_tokens", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_email_verification_tokens_user_id"), table_name="email_verification_tokens"
    )
    op.drop_table("email_verification_tokens")
    if op.get_context().dialect.name == "sqlite":
        op.execute("ALTER TABLE users DROP COLUMN email_verified_at")
    else:
        op.drop_column("users", "email_verified_at")
