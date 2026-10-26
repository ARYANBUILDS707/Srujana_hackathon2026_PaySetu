"""Business review (Phase 7C): reviewer grants, manual checks and decisions.

Every table here is append-only (SQLite triggers, migration 3d7a9c1e5b20): a decision or a
check is never edited or deleted; a correction is a new check. A reviewer grant may only be
revoked, once. Reviewer status is never set through the API: grants are created by the
operator CLI (`python -m tools.reviewer`).
"""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.entities import ID, TS

DECISIONS = ("APPROVED", "REJECTED", "NEEDS_INFORMATION")
CHECK_SOURCES = ("udyam_portal", "other_official_record", "certificate_only", "other")
CHECK_RESULTS = ("match", "mismatch", "not_found")
CHECK_FIELDS = (
    "udyam_number",
    "enterprise_name",
    "enterprise_class",
    "registration_date",
    "address",
    "representative_name",
)


def _in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


class ReviewerGrant(Base):
    """The reviewer role for one user. At most one active (unrevoked) grant per user."""

    __tablename__ = "reviewer_grants"
    __table_args__ = (
        Index(
            "uq_reviewer_grants_active_user",
            "user_id",
            unique=True,
            sqlite_where=text("revoked_at IS NULL"),
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[str] = mapped_column(TS)
    granted_by: Mapped[str] = mapped_column(String(120))  # operator label from the CLI
    revoked_at: Mapped[str | None] = mapped_column(TS)
    revoked_by: Mapped[str | None] = mapped_column(String(120))


class BusinessCheck(Base):
    """A manual check of one submission against a named source, by one reviewer."""

    __tablename__ = "business_checks"
    __table_args__ = (CheckConstraint(f"source IN ({_in(CHECK_SOURCES)})", name="source"),)

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("business_submissions.id"), index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(32))
    source_detail: Mapped[str] = mapped_column(String(300))  # what exactly was consulted
    checked_on: Mapped[date] = mapped_column(Date)  # when the reviewer looked (IST date)
    note: Mapped[str | None] = mapped_column(Text)  # reviewer-only
    recorded_at: Mapped[str] = mapped_column(TS)


class BusinessCheckItem(Base):
    """One field compared in a check: the submitted value (copied from the snapshot by the
    server), what the reviewer observed at the source, and the result."""

    __tablename__ = "business_check_items"
    __table_args__ = (
        CheckConstraint(f"field IN ({_in(CHECK_FIELDS)})", name="field"),
        CheckConstraint(f"result IN ({_in(CHECK_RESULTS)})", name="result"),
        UniqueConstraint("check_id", "field", name="uq_business_check_items_field"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    check_id: Mapped[str] = mapped_column(ForeignKey("business_checks.id"))
    field: Mapped[str] = mapped_column(String(32))
    submitted_value: Mapped[str | None] = mapped_column(String(500))
    observed_value: Mapped[str | None] = mapped_column(String(500))
    result: Mapped[str] = mapped_column(String(16))


class BusinessReview(Base):
    """A reviewer's decision on one submission. One per submission (unique), never changed."""

    __tablename__ = "business_reviews"
    __table_args__ = (
        CheckConstraint(f"decision IN ({_in(DECISIONS)})", name="decision"),
        UniqueConstraint("submission_id", name="uq_business_reviews_submission"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("business_submissions.id"))
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text)  # shown to the supplier
    internal_note: Mapped[str | None] = mapped_column(Text)  # reviewers only
    decided_at: Mapped[str] = mapped_column(TS)
