"""accounts and ownership

Revision ID: 099b88746350
Revises: 7f9909eb7e4c
Create Date: 2026-10-25 10:39:34.247147+00:00

Hand-reviewed (Phase 6). Adds `users` and `sessions` (DATABASE.md 3.1-3.2) and
`suppliers.owner_user_id`.

Existing data is preserved and NOT assigned to anyone: the new column is nullable, so suppliers
created before accounts existed (the seeded demo supplier) stay unowned and unreachable through
the API until an operator assigns the demo supplier explicitly with `make demo-account`. Only a
demo supplier may be unowned: a CHECK on PostgreSQL, triggers on SQLite (SQLite cannot add a
CHECK to an existing table without rebuilding it, and rebuilding `suppliers` would mean
dropping a table that `buyers` and `cases` reference).

On SQLite the column is added with `ALTER TABLE ... ADD COLUMN ... REFERENCES`, so no table is
rebuilt and no existing row is rewritten.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "099b88746350"
down_revision: str | Sequence[str] | None = "7f9909eb7e4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OWNERSHIP_TRIGGERS = {
    "trg_suppliers_owned_unless_demo_insert": "BEFORE INSERT ON suppliers",
    "trg_suppliers_owned_unless_demo_update": (
        "BEFORE UPDATE OF owner_user_id, is_demo ON suppliers"
    ),
}


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("terms_version", sa.String(length=32), nullable=False),
        sa.Column("terms_accepted_at", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("last_seen_at", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.String(length=32), nullable=False),
        sa.Column("revoked_at", sa.String(length=32), nullable=True),
        sa.Column("user_agent", sa.String(length=200), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    if op.get_context().dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE suppliers ADD COLUMN owner_user_id VARCHAR(36) "
            "REFERENCES users (id)"
        )
        for name, timing in _OWNERSHIP_TRIGGERS.items():
            op.execute(
                f"CREATE TRIGGER {name} {timing} "
                "WHEN NEW.is_demo = 0 AND NEW.owner_user_id IS NULL "
                "BEGIN SELECT RAISE(ABORT, 'only a demo supplier may be unowned'); END"
            )
    else:
        op.add_column("suppliers", sa.Column("owner_user_id", sa.String(length=36)))
        op.create_foreign_key(
            op.f("fk_suppliers_owner_user_id_users"),
            "suppliers",
            "users",
            ["owner_user_id"],
            ["id"],
        )
        op.create_check_constraint(
            op.f("ck_suppliers_owned_unless_demo"),
            "suppliers",
            "is_demo = true OR owner_user_id IS NOT NULL",
        )
    op.create_index(
        "uq_suppliers_owner_user_id", "suppliers", ["owner_user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_suppliers_owner_user_id", table_name="suppliers")
    if op.get_context().dialect.name == "sqlite":
        for name in _OWNERSHIP_TRIGGERS:
            op.execute(f"DROP TRIGGER IF EXISTS {name}")
        op.execute("ALTER TABLE suppliers DROP COLUMN owner_user_id")
    else:
        op.drop_constraint(op.f("ck_suppliers_owned_unless_demo"), "suppliers", type_="check")
        op.drop_constraint(
            op.f("fk_suppliers_owner_user_id_users"), "suppliers", type_="foreignkey"
        )
        op.drop_column("suppliers", "owner_user_id")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
