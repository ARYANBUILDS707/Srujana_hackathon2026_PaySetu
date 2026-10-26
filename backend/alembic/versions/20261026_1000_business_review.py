"""business review

Revision ID: 3d7a9c1e5b20
Revises: 8e1f3c9a2b64
Create Date: 2026-10-26 10:00:00.000000+00:00

Hand-reviewed (Phase 7C). Adds the reviewer workflow without touching existing rows other
than the status rename below:

- New tables `reviewer_grants`, `business_checks`, `business_check_items`, `business_reviews`.
  No grant is created: reviewers exist only once an operator runs `python -m tools.reviewer`.
- `business_profiles.status`: the never-used `VERIFIED` value is renamed `APPROVED` (a reviewer
  decision, not a government verification). Any row that somehow holds `VERIFIED` is mapped to
  `APPROVED` in between two table rebuilds, so no row can be lost; no code path ever wrote it.
  SQLite rebuilds the table from an explicit definition (works offline too); other databases
  swap the CHECK constraint in place.

SQLite triggers:
- `business_reviews`, `business_checks`, `business_check_items`: no UPDATE, no DELETE.
- `reviewer_grants`: no DELETE; only `revoked_at`/`revoked_by` may change, and only once.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d7a9c1e5b20"
down_revision: str | Sequence[str] | None = "8e1f3c9a2b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUSES = ("DRAFT", "PENDING_REVIEW", "NEEDS_INFORMATION", "VERIFIED", "REJECTED")
NEW_STATUSES = ("DRAFT", "PENDING_REVIEW", "NEEDS_INFORMATION", "APPROVED", "REJECTED")
BOTH_STATUSES = (*OLD_STATUSES, "APPROVED")


def _no_change(table: str, message: str) -> dict[str, str]:
    return {
        f"{table}_no_update": (
            f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
        ),
        f"{table}_no_delete": (
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
        ),
    }


SQLITE_TRIGGERS = {
    **_no_change("business_reviews", "business_reviews are immutable"),
    **_no_change("business_checks", "business_checks are immutable"),
    **_no_change("business_check_items", "business_check_items are immutable"),
    "reviewer_grants_no_delete": (
        "CREATE TRIGGER reviewer_grants_no_delete BEFORE DELETE ON reviewer_grants "
        "BEGIN SELECT RAISE(ABORT, 'reviewer_grants are kept for audit'); END"
    ),
    "reviewer_grants_revoke_only": (
        "CREATE TRIGGER reviewer_grants_revoke_only BEFORE UPDATE ON reviewer_grants "
        "WHEN OLD.revoked_at IS NOT NULL OR NEW.id IS NOT OLD.id "
        "OR NEW.user_id IS NOT OLD.user_id OR NEW.granted_at IS NOT OLD.granted_at "
        "OR NEW.granted_by IS NOT OLD.granted_by "
        "BEGIN SELECT RAISE(ABORT, 'reviewer_grants may only be revoked, once'); END"
    ),
}


def _in(values: Sequence[str]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def _profiles_table(statuses: Sequence[str]) -> sa.Table:
    """`business_profiles` exactly as migration 8e1f3c9a2b64 created it, with `statuses`."""
    return sa.Table(
        "business_profiles",
        sa.MetaData(),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("enterprise_name", sa.String(length=200), nullable=True),
        sa.Column("udyam_number", sa.String(length=19), nullable=True),
        sa.Column("enterprise_class", sa.String(length=8), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("address_line1", sa.String(length=200), nullable=True),
        sa.Column("address_line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("pin_code", sa.String(length=6), nullable=True),
        sa.Column("contact_email", sa.String(length=254), nullable=True),
        sa.Column("contact_phone", sa.String(length=16), nullable=True),
        sa.Column("representative_name", sa.String(length=120), nullable=True),
        sa.Column("representative_role", sa.String(length=32), nullable=True),
        sa.Column("authorisation_note", sa.String(length=500), nullable=True),
        sa.Column("authority_confirmed", sa.Boolean(), nullable=False),
        sa.Column("certificate_id", sa.String(length=36), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.String(length=32), nullable=True),
        sa.Column("status_changed_at", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint(f"status IN ({_in(statuses)})", name="ck_business_profiles_status"),
        sa.CheckConstraint(
            "enterprise_class IS NULL OR enterprise_class IN ('micro', 'small', 'medium')",
            name="ck_business_profiles_enterprise_class",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["business_certificates.id"],
            name="fk_business_profiles_certificate_id_business_certificates",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name="fk_business_profiles_supplier_id_suppliers"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_business_profiles"),
        sa.UniqueConstraint("supplier_id", name="uq_business_profiles_supplier_id"),
    )


def _set_statuses(statuses: Sequence[str]) -> None:
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table(
            "business_profiles", copy_from=_profiles_table(statuses), recreate="always"
        ):
            pass
        return
    op.drop_constraint(op.f("ck_business_profiles_status"), "business_profiles", type_="check")
    op.create_check_constraint(
        op.f("ck_business_profiles_status"), "business_profiles", f"status IN ({_in(statuses)})"
    )


def _rename_status(old: str, new: str, final: Sequence[str]) -> None:
    _set_statuses(BOTH_STATUSES)
    op.execute(f"UPDATE business_profiles SET status = '{new}' WHERE status = '{old}'")
    _set_statuses(final)


def upgrade() -> None:
    _rename_status("VERIFIED", "APPROVED", NEW_STATUSES)
    op.create_table(
        "reviewer_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("granted_at", sa.String(length=32), nullable=False),
        sa.Column("granted_by", sa.String(length=120), nullable=False),
        sa.Column("revoked_at", sa.String(length=32), nullable=True),
        sa.Column("revoked_by", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_reviewer_grants_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviewer_grants")),
    )
    op.create_index(
        "uq_reviewer_grants_active_user",
        "reviewer_grants",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("revoked_at IS NULL"),
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "business_checks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_detail", sa.String(length=300), nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "source IN ('udyam_portal', 'other_official_record', 'certificate_only', 'other')",
            name=op.f("ck_business_checks_source"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name=op.f("fk_business_checks_reviewer_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["business_submissions.id"],
            name=op.f("fk_business_checks_submission_id_business_submissions"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_business_checks_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_checks")),
    )
    op.create_index(op.f("ix_business_checks_submission_id"), "business_checks", ["submission_id"])
    op.create_table(
        "business_check_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("check_id", sa.String(length=36), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.Column("submitted_value", sa.String(length=500), nullable=True),
        sa.Column("observed_value", sa.String(length=500), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "field IN ('udyam_number', 'enterprise_name', 'enterprise_class', "
            "'registration_date', 'address', 'representative_name')",
            name=op.f("ck_business_check_items_field"),
        ),
        sa.CheckConstraint(
            "result IN ('match', 'mismatch', 'not_found')",
            name=op.f("ck_business_check_items_result"),
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["business_checks.id"],
            name=op.f("fk_business_check_items_check_id_business_checks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_check_items")),
        sa.UniqueConstraint("check_id", "field", name="uq_business_check_items_field"),
    )
    op.create_table(
        "business_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED', 'NEEDS_INFORMATION')",
            name=op.f("ck_business_reviews_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name=op.f("fk_business_reviews_reviewer_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["business_submissions.id"],
            name=op.f("fk_business_reviews_submission_id_business_submissions"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_business_reviews_supplier_id_suppliers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_reviews")),
        sa.UniqueConstraint("submission_id", name="uq_business_reviews_submission"),
    )
    op.create_index(op.f("ix_business_reviews_supplier_id"), "business_reviews", ["supplier_id"])
    if op.get_context().dialect.name == "sqlite":
        for statement in SQLITE_TRIGGERS.values():
            op.execute(statement)


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        for name in SQLITE_TRIGGERS:
            op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.drop_index(op.f("ix_business_reviews_supplier_id"), table_name="business_reviews")
    op.drop_table("business_reviews")
    op.drop_table("business_check_items")
    op.drop_index(op.f("ix_business_checks_submission_id"), table_name="business_checks")
    op.drop_table("business_checks")
    op.drop_index("uq_reviewer_grants_active_user", table_name="reviewer_grants")
    op.drop_table("reviewer_grants")
    _rename_status("APPROVED", "VERIFIED", OLD_STATUSES)
