"""Business onboarding (Phase 7B): profile drafts, certificates, submissions, Udyam claims.

Kept apart from the supplier's eligibility fields (`suppliers.udyam_*`), which the legal
engine reads: nothing a supplier submits here changes eligibility, cases or packs. Status
values are written by the server only; VERIFIED, REJECTED and NEEDS_INFORMATION are reserved
for reviewers (Phase 7C) and no supplier-facing code path sets them.
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.entities import HASH, ID, TS

STATUSES = ("DRAFT", "PENDING_REVIEW", "NEEDS_INFORMATION", "VERIFIED", "REJECTED")
_STATUS_SQL = ", ".join(f"'{s}'" for s in STATUSES)


class BusinessCertificate(Base):
    """An uploaded Udyam certificate PDF. Append-only: replacing one adds a new row."""

    __tablename__ = "business_certificates"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))  # display only
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(HASH)
    storage_key: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[str] = mapped_column(TS)
    uploaded_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class BusinessProfile(Base):
    """The supplier's onboarding record: the current draft plus its review status."""

    __tablename__ = "business_profiles"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="status"),
        CheckConstraint(
            "enterprise_class IS NULL OR enterprise_class IN ('micro', 'small', 'medium')",
            name="enterprise_class",
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), unique=True)
    status: Mapped[str] = mapped_column(String(24))
    enterprise_name: Mapped[str | None] = mapped_column(String(200))
    udyam_number: Mapped[str | None] = mapped_column(String(19))  # normalised
    enterprise_class: Mapped[str | None] = mapped_column(String(8))  # self-declared
    registration_date: Mapped[date | None] = mapped_column(Date)
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    pin_code: Mapped[str | None] = mapped_column(String(6))
    contact_email: Mapped[str | None] = mapped_column(String(254))
    contact_phone: Mapped[str | None] = mapped_column(String(16))
    representative_name: Mapped[str | None] = mapped_column(String(120))
    representative_role: Mapped[str | None] = mapped_column(String(32))
    authorisation_note: Mapped[str | None] = mapped_column(String(500))
    authority_confirmed: Mapped[bool] = mapped_column(Boolean)
    certificate_id: Mapped[str | None] = mapped_column(ForeignKey("business_certificates.id"))
    revision: Mapped[int] = mapped_column(Integer)  # number of submissions so far
    submitted_at: Mapped[str | None] = mapped_column(TS)
    status_changed_at: Mapped[str] = mapped_column(TS)
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class BusinessSubmission(Base):
    """An immutable snapshot of what was submitted for review (triggers forbid changes)."""

    __tablename__ = "business_submissions"
    __table_args__ = (
        UniqueConstraint("supplier_id", "revision", name="uq_business_submissions_rev"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    udyam_number: Mapped[str] = mapped_column(String(19))
    certificate_id: Mapped[str] = mapped_column(ForeignKey("business_certificates.id"))
    claim_contested: Mapped[bool] = mapped_column(Boolean)
    snapshot: Mapped[str] = mapped_column(Text)  # canonical JSON
    snapshot_sha256: Mapped[str] = mapped_column(HASH)
    submitted_at: Mapped[str] = mapped_column(TS)
    submitted_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class UdyamClaim(Base):
    """One row per (supplier, Udyam number) ever submitted.

    At most one UNCONTESTED claim per number (partial unique index). A second supplier who
    submits the same number gets a CONTESTED claim: the submission still goes to review, where
    the dispute is resolved (Phase 7C); it is never silently rejected or merged.
    """

    __tablename__ = "udyam_claims"
    __table_args__ = (
        UniqueConstraint("supplier_id", "udyam_number", name="uq_udyam_claims_supplier_number"),
        Index(
            "uq_udyam_claims_uncontested_number",
            "udyam_number",
            unique=True,
            sqlite_where=text("contested = 0"),
            postgresql_where=text("contested = false"),
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    udyam_number: Mapped[str] = mapped_column(String(19))
    contested: Mapped[bool] = mapped_column(Boolean)
    first_submitted_at: Mapped[str] = mapped_column(TS)
