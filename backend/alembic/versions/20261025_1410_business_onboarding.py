"""business onboarding

Revision ID: 8e1f3c9a2b64
Revises: 5c2e8a41f0b7
Create Date: 2026-10-25 14:10:00.000000+00:00

Hand-reviewed (Phase 7B). Creates `business_certificates`, `business_profiles`,
`business_submissions` and `udyam_claims`. Creates new tables only: no existing row is read or
changed, and no supplier gets a profile (every existing supplier starts at NOT_STARTED; none
is marked VERIFIED). The supplier eligibility fields (`suppliers.udyam_*`) are untouched.

SQLite triggers (as for evidence and the timeline):
- `business_submissions`: no UPDATE, no DELETE (immutable snapshots).
- `business_certificates`: no DELETE; no UPDATE of any column (append-only metadata).
- `udyam_claims`: no DELETE; only `contested` may change (reserved for review in Phase 7C).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e1f3c9a2b64"
down_revision: str | Sequence[str] | None = "5c2e8a41f0b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = "'DRAFT', 'PENDING_REVIEW', 'NEEDS_INFORMATION', 'VERIFIED', 'REJECTED'"

SQLITE_TRIGGERS = {
    "business_submissions_no_update": (
        "CREATE TRIGGER business_submissions_no_update BEFORE UPDATE ON business_submissions "
        "BEGIN SELECT RAISE(ABORT, 'business_submissions are immutable'); END"
    ),
    "business_submissions_no_delete": (
        "CREATE TRIGGER business_submissions_no_delete BEFORE DELETE ON business_submissions "
        "BEGIN SELECT RAISE(ABORT, 'business_submissions are immutable'); END"
    ),
    "business_certificates_no_update": (
        "CREATE TRIGGER business_certificates_no_update BEFORE UPDATE ON business_certificates "
        "BEGIN SELECT RAISE(ABORT, 'business_certificates are append-only'); END"
    ),
    "business_certificates_no_delete": (
        "CREATE TRIGGER business_certificates_no_delete BEFORE DELETE ON business_certificates "
        "BEGIN SELECT RAISE(ABORT, 'business_certificates are append-only'); END"
    ),
    "udyam_claims_no_delete": (
        "CREATE TRIGGER udyam_claims_no_delete BEFORE DELETE ON udyam_claims "
        "BEGIN SELECT RAISE(ABORT, 'udyam_claims are kept for review'); END"
    ),
    "udyam_claims_contested_only": (
        "CREATE TRIGGER udyam_claims_contested_only BEFORE UPDATE OF id, supplier_id, "
        "udyam_number, first_submitted_at ON udyam_claims "
        "BEGIN SELECT RAISE(ABORT, 'udyam_claims may only change contested'); END"
    ),
}


def upgrade() -> None:
    op.create_table(
        "business_certificates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_business_certificates_supplier_id_suppliers"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_business_certificates_uploaded_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_certificates")),
    )
    op.create_index(
        op.f("ix_business_certificates_supplier_id"), "business_certificates", ["supplier_id"]
    )
    op.create_table(
        "business_profiles",
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
        sa.CheckConstraint(f"status IN ({STATUSES})", name=op.f("ck_business_profiles_status")),
        sa.CheckConstraint(
            "enterprise_class IS NULL OR enterprise_class IN ('micro', 'small', 'medium')",
            name=op.f("ck_business_profiles_enterprise_class"),
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["business_certificates.id"],
            name=op.f("fk_business_profiles_certificate_id_business_certificates"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_business_profiles_supplier_id_suppliers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_profiles")),
        sa.UniqueConstraint("supplier_id", name=op.f("uq_business_profiles_supplier_id")),
    )
    op.create_table(
        "business_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("udyam_number", sa.String(length=19), nullable=False),
        sa.Column("certificate_id", sa.String(length=36), nullable=False),
        sa.Column("claim_contested", sa.Boolean(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("submitted_at", sa.String(length=32), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["business_certificates.id"],
            name=op.f("fk_business_submissions_certificate_id_business_certificates"),
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name=op.f("fk_business_submissions_submitted_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_business_submissions_supplier_id_suppliers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_business_submissions")),
        sa.UniqueConstraint("supplier_id", "revision", name="uq_business_submissions_rev"),
    )
    op.create_index(
        op.f("ix_business_submissions_supplier_id"), "business_submissions", ["supplier_id"]
    )
    op.create_table(
        "udyam_claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("udyam_number", sa.String(length=19), nullable=False),
        sa.Column("contested", sa.Boolean(), nullable=False),
        sa.Column("first_submitted_at", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_udyam_claims_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_udyam_claims")),
        sa.UniqueConstraint(
            "supplier_id", "udyam_number", name="uq_udyam_claims_supplier_number"
        ),
    )
    op.create_index(op.f("ix_udyam_claims_supplier_id"), "udyam_claims", ["supplier_id"])
    op.create_index(
        "uq_udyam_claims_uncontested_number",
        "udyam_claims",
        ["udyam_number"],
        unique=True,
        sqlite_where=sa.text("contested = 0"),
        postgresql_where=sa.text("contested = false"),
    )
    if op.get_bind().dialect.name == "sqlite":
        for statement in SQLITE_TRIGGERS.values():
            op.execute(statement)


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for name in SQLITE_TRIGGERS:
            op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.drop_index("uq_udyam_claims_uncontested_number", table_name="udyam_claims")
    op.drop_index(op.f("ix_udyam_claims_supplier_id"), table_name="udyam_claims")
    op.drop_table("udyam_claims")
    op.drop_index(op.f("ix_business_submissions_supplier_id"), table_name="business_submissions")
    op.drop_table("business_submissions")
    op.drop_table("business_profiles")
    op.drop_index(op.f("ix_business_certificates_supplier_id"), table_name="business_certificates")
    op.drop_table("business_certificates")
