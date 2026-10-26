"""Schemas for business review (Phase 7C; API.md "Business review").

Inputs forbid unknown fields (422): a payload can never name a reviewer, a supplier, a status
or a submitted value. The reviewer is always the session's user; submitted values are copied
from the immutable snapshot by the server.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.business_review import CheckResult, CheckSource, EvidenceLevel
from app.schemas.onboarding import CertificateOut, EnterpriseClass, RepresentativeRole

Decision = Literal["APPROVED", "REJECTED", "NEEDS_INFORMATION"]
SubmissionStatus = Literal["PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_INFORMATION"]
CheckField = Literal[
    "udyam_number",
    "enterprise_name",
    "enterprise_class",
    "registration_date",
    "address",
    "representative_name",
]

Text300 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
Text500 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckItemIn(_In):
    field: CheckField
    observed_value: Text500 | None = None  # what the reviewer saw at the source
    result: CheckResult

    @model_validator(mode="after")
    def _observed_needed(self) -> "CheckItemIn":
        if self.result is not CheckResult.NOT_FOUND and self.observed_value is None:
            raise ValueError("Record the value you saw at the source for a match or mismatch.")
        return self


class CheckIn(_In):
    """A manual check: which source, what exactly, when, and what was compared."""

    source: CheckSource
    source_detail: Text300  # e.g. the portal page or record consulted
    checked_on: date  # not in the future (checked by the service against the IST date)
    items: list[CheckItemIn] = Field(min_length=1, max_length=6)
    note: Note | None = None

    @model_validator(mode="after")
    def _unique_fields(self) -> "CheckIn":
        fields = [item.field for item in self.items]
        if len(fields) != len(set(fields)):
            raise ValueError("Each field can be compared only once per check.")
        return self


class DecisionIn(_In):
    decision: Decision
    reason: Reason  # shown to the supplier for NEEDS_INFORMATION and REJECTED
    internal_note: Note | None = None  # reviewers only; never shown to the supplier


class PersonOut(BaseModel):
    id: str
    full_name: str
    email: str


class QueueItemOut(BaseModel):
    submission_id: str
    supplier_id: str
    revision: int
    enterprise_name: str | None
    udyam_number: str
    submitted_at: str
    status: SubmissionStatus
    claim_contested: bool  # as recorded at submission
    other_claimants: int  # other suppliers who have submitted the same Udyam number
    checks_recorded: int
    own_submission: bool  # the reviewer owns or submitted it: they cannot decide it


class QueuePageOut(BaseModel):
    items: list[QueueItemOut]
    next_cursor: str | None


class SubmittedProfileOut(BaseModel):
    """The supplier's details exactly as frozen in the submission snapshot."""

    enterprise_name: str | None
    udyam_number: str | None
    enterprise_class: EnterpriseClass | None
    registration_date: date | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    pin_code: str | None
    contact_email: str | None
    contact_phone: str | None
    representative_name: str | None
    representative_role: RepresentativeRole | None
    authorisation_note: str | None
    authority_confirmed: bool


class ReviewCertificateOut(CertificateOut):
    # The stored bytes still hash to the recorded SHA-256. Integrity only: it says nothing
    # about whether the certificate is genuine.
    bytes_intact: bool


class OtherClaimOut(BaseModel):
    supplier_id: str
    submission_id: str | None  # that supplier's latest submission with this number
    enterprise_name: str | None
    profile_status: str
    contested: bool


class CheckItemOut(BaseModel):
    field: CheckField
    submitted_value: str | None
    observed_value: str | None
    result: CheckResult


class CheckOut(BaseModel):
    id: str
    reviewer: PersonOut
    source: CheckSource
    official_source: bool
    source_detail: str
    checked_on: date
    recorded_at: str
    note: str | None
    items: list[CheckItemOut]


class DecisionOut(BaseModel):
    id: str
    submission_id: str
    revision: int
    decision: Decision
    reason: str
    internal_note: str | None
    reviewer: PersonOut
    decided_at: str


class HistoryItemOut(BaseModel):
    submission_id: str
    revision: int
    submitted_at: str
    snapshot_sha256: str
    status: SubmissionStatus
    decision: DecisionOut | None


class ReviewDetailOut(BaseModel):
    submission_id: str
    supplier_id: str
    revision: int
    status: SubmissionStatus
    profile_status: str  # the supplier's current onboarding status
    submitted_at: str
    submitted_by: PersonOut
    snapshot_sha256: str
    snapshot_intact: bool  # the stored snapshot still hashes to its recorded SHA-256
    notice: str  # the self-declaration notice frozen in the snapshot
    profile: SubmittedProfileOut
    certificate: ReviewCertificateOut
    claim_contested: bool  # as recorded at submission
    other_claims: list[OtherClaimOut]
    checks: list[CheckOut]
    evidence_level: EvidenceLevel
    decision: DecisionOut | None
    own_submission: bool
    allowed_decisions: list[Decision]
    approval_blockers: list[str]
    history: list[HistoryItemOut]
