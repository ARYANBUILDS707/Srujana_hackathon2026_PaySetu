"""Request and response schemas for the demo vertical slice (API.md Sections 2.3–2.10)."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.types import (
    DealType,
    EnterpriseClass,
    EvidenceKind,
    MajorActivity,
    ResponseChannel,
    ResponseKind,
    UdyamVerificationStatus,
)

Text60 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Text200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Gstin = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        pattern=r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$",
    ),
]
Money = Annotated[Decimal, Field(gt=0, le=Decimal("10000000000.00"), decimal_places=2)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BuyerCreate(_In):
    legal_name: Text200
    gstin: Gstin | None = None
    contact_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None
    ) = None
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254)] | None = None


class CaseCreate(_In):
    buyer_id: str
    invoice_number: Text60
    invoice_date: date
    invoice_amount: Money
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = (
        None
    )
    delivery_date: date
    delivery_location: Text200 | None = None
    deal_type: DealType
    agreed_payment_days: int | None = Field(default=None, ge=0, le=365)
    agreed_due_date: date | None = None


class ResponseCreate(_In):
    kind: ResponseKind
    received_on: date
    channel: ResponseChannel
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    evidence_item_id: str | None = None


class ObjectionRemoval(_In):
    removed_on: date


# ---------------------------------------------------------------------------- outputs


class SupplierOut(BaseModel):
    id: str
    legal_name: str
    udyam_number: str | None
    enterprise_class: EnterpriseClass | None
    major_activity: MajorActivity | None
    udyam_registration_date: date | None
    udyam_verification_status: UdyamVerificationStatus
    eligibility_verdict: str
    eligibility_reasons: list[dict[str, str]]
    demo_mode: bool = True


class BuyerOut(BaseModel):
    id: str
    legal_name: str
    gstin: str | None
    contact_name: str | None
    email: str | None


class ExplanationOut(BaseModel):
    field: str
    rule_ids: list[str]
    text: str


class ClockOut(BaseModel):
    as_of: date
    rule_set_version: str
    acceptance_state: str
    acceptance_basis: str | None
    window_end: date
    window_day: int | None
    window_days_remaining: int | None
    acceptance_date: date | None
    due_date: date | None
    interest_start: date | None
    indicative_limitation_date: date | None
    payment_state: str | None
    days_overdue: int | None
    terms_capped_at_45: bool
    explanations: list[ExplanationOut]
    unconfirmed_rules: list[str]
    pending_reviews: list[str]


class AmountsOut(BaseModel):
    as_of: date
    principal: str
    paid: str
    outstanding_principal: str
    interest: str | None
    total_claimable: str | None
    interest_status: str
    uses_unverified_rates: bool
    illustrative: bool = True


class ChecklistItemOut(BaseModel):
    item_id: str
    title: str
    level: str
    status: str
    action: str | None


class ChecklistOut(BaseModel):
    required_met: int
    required_total: int
    warnings: int
    items: list[ChecklistItemOut]
    unconfirmed_rules: list[str]


class NextActionOut(BaseModel):
    code: str
    checklist_item: str | None
    until: date | None


class CaseSummaryOut(BaseModel):
    id: str
    reference: str
    buyer: BuyerOut
    invoice_number: str
    invoice_amount: str
    delivery_date: date
    acceptance_state: str
    payment_state: str | None
    due_date: date | None
    demo_mode: bool = True


class CaseOut(CaseSummaryOut):
    lifecycle: str
    invoice_date: date
    description: str | None
    delivery_location: str | None
    deal_type: DealType
    agreed_payment_days: int | None
    agreed_due_date: date | None
    recorded_late_days: int
    rule_set_version: str
    clock: ClockOut
    amounts: AmountsOut
    checklist_summary: dict[str, int]
    next_action: NextActionOut
    has_simulated_items: bool


class ResponseOut(BaseModel):
    id: str
    kind: ResponseKind
    received_on: date
    channel: ResponseChannel
    summary: str
    evidence_item_id: str | None
    objection_removed_on: date | None
    within_window: bool
    counts_as_written: bool
    affects_acceptance: bool
    note: str


class EvidenceOut(BaseModel):
    id: str
    kind: EvidenceKind
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    received_at: str
    note: str | None
    excluded: bool


class TimelineEventOut(BaseModel):
    seq: int
    event_type: str
    occurred_on: date | None
    recorded_at: str
    actor_type: str
    payload: dict[str, object]
    prev_hash: str
    event_hash: str


class MismatchOut(BaseModel):
    type: str
    reference: str
    detail: str


class IntegrityOut(BaseModel):
    result: str
    checked_files: int
    checked_events: int
    mismatches: list[MismatchOut]
    timeline_head_hash: str | None
    recorded_event_seq: int


class InterestPeriodOut(BaseModel):
    start: date
    end: date
    days: int
    kind: str
    bank_rate_percent: str
    annual_rate_percent: str
    rate_verified: bool
    opening_balance: str
    interest: str
    closing_principal: str
    closing_interest: str


class InterestOut(BaseModel):
    status: str
    as_of: date
    interest_start: date | None
    principal: str
    interest_accrued: str | None
    total_outstanding: str | None
    uses_unverified_rates: bool
    periods: list[InterestPeriodOut]
    unconfirmed_rules: list[str]
    pending_reviews: list[str]
    message: str
    illustrative: bool = True
