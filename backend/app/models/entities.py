"""Tables for the demo vertical slice (DATABASE.md Sections 3.4–3.15, subset).

Deviations from DATABASE.md:
- `suppliers.owner_user_id` is nullable (Phase 6). Only a demo supplier may be unowned (CHECK
  `owned_unless_demo`): rows created before accounts existed stay unowned, and so unreachable
  through the API, until an operator assigns them explicitly (`make demo-account`).
- `suppliers` has an `is_demo` flag.
- `bank_rates` has a `verified` flag and nullable `verified_by`, so unverified illustrative
  rates can be stored honestly labelled.
- payments, communications, packs and share links are not created yet.
Timestamps are ISO-8601 UTC strings with a `Z` suffix; money is integer paise.
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ID = String(36)
TS = String(32)
HASH = String(64)


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        # SQLite enforces this rule with triggers (migration 099b88746350).
        CheckConstraint("is_demo = 1 OR owner_user_id IS NOT NULL", name="owned_unless_demo"),
        Index("uq_suppliers_owner_user_id", "owner_user_id", unique=True),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    # One supplier per user (PRD D14). Set from the session, never from request data.
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    legal_name: Mapped[str] = mapped_column(String(200))
    trade_name: Mapped[str | None] = mapped_column(String(200))
    udyam_number: Mapped[str | None] = mapped_column(String(32))
    enterprise_class: Mapped[str | None] = mapped_column(String(16))
    major_activity: Mapped[str | None] = mapped_column(String(16))
    udyam_registration_date: Mapped[date | None] = mapped_column(Date)
    udyam_verification_status: Mapped[str] = mapped_column(String(32))
    gstin: Mapped[str | None] = mapped_column(String(15))
    contact_email: Mapped[str] = mapped_column(String(254))
    is_demo: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = (UniqueConstraint("supplier_id", "id", name="uq_buyers_supplier_id_id"),)

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    legal_name: Mapped[str] = mapped_column(String(200))
    gstin: Mapped[str | None] = mapped_column(String(15))
    contact_name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supplier_id", "buyer_id"],
            ["buyers.supplier_id", "buyers.id"],
            name="fk_cases_supplier_buyer",
        ),
        UniqueConstraint("supplier_id", "reference", name="uq_cases_supplier_id_reference"),
        CheckConstraint("invoice_amount_paise > 0", name="invoice_amount_positive"),
        CheckConstraint("deal_type IN ('verbal', 'written')", name="deal_type"),
        CheckConstraint(
            "deal_type = 'written' OR (agreed_payment_days IS NULL AND agreed_due_date IS NULL)",
            name="verbal_has_no_terms",
        ),
        CheckConstraint("lifecycle IN ('open', 'closed')", name="lifecycle"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    buyer_id: Mapped[str] = mapped_column(ID)
    reference: Mapped[str] = mapped_column(String(16))
    rule_set_version: Mapped[str] = mapped_column(String(16))
    invoice_number: Mapped[str] = mapped_column(String(60))
    invoice_date: Mapped[date] = mapped_column(Date)
    invoice_amount_paise: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(500))
    delivery_date: Mapped[date] = mapped_column(Date)
    delivery_location: Mapped[str | None] = mapped_column(String(200))
    deal_type: Mapped[str] = mapped_column(String(16))
    agreed_payment_days: Mapped[int | None] = mapped_column(Integer)
    agreed_due_date: Mapped[date | None] = mapped_column(Date)
    lifecycle: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        UniqueConstraint("case_id", "sha256", name="uq_evidence_items_case_id_sha256"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"))
    kind: Mapped[str] = mapped_column(String(32))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(HASH)
    storage_key: Mapped[str] = mapped_column(String(255))
    received_at: Mapped[str] = mapped_column(TS)
    note: Mapped[str | None] = mapped_column(String(500))
    excluded_at: Mapped[str | None] = mapped_column(TS)
    excluded_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[str] = mapped_column(TS)


class BuyerResponse(Base):
    __tablename__ = "buyer_responses"
    __table_args__ = (
        CheckConstraint(
            "objection_removed_on IS NULL OR kind = 'objection'", name="removal_only_objection"
        ),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    received_on: Mapped[date] = mapped_column(Date)
    channel: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(String(1000))
    evidence_item_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_items.id"))
    objection_removed_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class TimelineEventRow(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (UniqueConstraint("case_id", "seq", name="uq_timeline_events_case_id_seq"),)

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(48))
    occurred_on: Mapped[date | None] = mapped_column(Date)
    recorded_at: Mapped[str] = mapped_column(TS)
    actor_type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str | None] = mapped_column(ID)
    payload: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(HASH)
    event_hash: Mapped[str] = mapped_column(HASH)


class BankRate(Base):
    __tablename__ = "bank_rates"
    __table_args__ = (
        CheckConstraint("rate_bps BETWEEN 1 AND 5000", name="rate_range"),
        CheckConstraint("verified = 0 OR verified_by IS NOT NULL", name="verified_has_verifier"),
    )

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    effective_from: Mapped[date] = mapped_column(Date, unique=True)
    rate_bps: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean)
    verified_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[str] = mapped_column(TS)
