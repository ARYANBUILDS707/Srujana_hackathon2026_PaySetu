"""Schemas for business onboarding (Phase 7B).

`DraftIn` lists every field a supplier may write. Unknown fields are rejected (422), so status,
owner, reviewer or verification fields can never be set from a client payload.
"""

import re
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.schemas.auth import valid_email

_UDYAM_CORE = re.compile(r"^UDYAM([A-Z]{2})(\d{2})(\d{7})$")
_SEPARATORS = re.compile(r"[\s\-_/.]")
_PIN = re.compile(r"^[1-9]\d{5}$")
_MOBILE = re.compile(r"^(?:\+?91)?([6-9]\d{9})$")

UDYAM_FORMAT_HELP = (
    "Enter the Udyam Registration Number as UDYAM-XX-00-0000000 "
    "(two letters, two digits, seven digits)."
)


def normalise_udyam(value: str) -> str:
    """`udyam mh 12 0001234` → `UDYAM-MH-12-0001234`; ValueError if the format is wrong.

    A well-formed number is not proof that the registration exists or belongs to anyone.
    """
    core = _SEPARATORS.sub("", value).upper()
    match = _UDYAM_CORE.fullmatch(core)
    if not match:
        raise ValueError(UDYAM_FORMAT_HELP)
    return f"UDYAM-{match.group(1)}-{match.group(2)}-{match.group(3)}"


class EnterpriseClass(StrEnum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"


class RepresentativeRole(StrEnum):
    PROPRIETOR = "proprietor"
    PARTNER = "partner"
    DESIGNATED_PARTNER = "designated_partner"
    DIRECTOR = "director"
    AUTHORISED_SIGNATORY = "authorised_signatory"
    OTHER = "other"


Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Text200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text500 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class DraftIn(BaseModel):
    """A full draft (PUT semantics: an omitted field is cleared). Everything is optional for a
    draft; the required set is checked on submission."""

    model_config = ConfigDict(extra="forbid")

    enterprise_name: Text200 | None = None
    udyam_number: str | None = None
    enterprise_class: EnterpriseClass | None = None
    registration_date: date | None = None
    address_line1: Text200 | None = None
    address_line2: Text200 | None = None
    city: Text100 | None = None
    state: Text100 | None = None
    pin_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    representative_name: Text120 | None = None
    representative_role: RepresentativeRole | None = None
    authorisation_note: Text500 | None = None
    authority_confirmed: bool = False

    @field_validator("udyam_number")
    @classmethod
    def _udyam(cls, value: str | None) -> str | None:
        return normalise_udyam(value) if value and value.strip() else None

    @field_validator("pin_code")
    @classmethod
    def _pin(cls, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        pin = value.replace(" ", "")
        if not _PIN.fullmatch(pin):
            raise ValueError("Enter the 6-digit PIN code.")
        return pin

    @field_validator("contact_email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        email = value.strip().lower()
        if not valid_email(email):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("contact_phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        if not value or not value.strip():
            return None
        match = _MOBILE.fullmatch(_SEPARATORS.sub("", value).replace("(", "").replace(")", ""))
        if not match:
            raise ValueError("Enter a 10-digit Indian mobile number, optionally with +91.")
        return f"+91{match.group(1)}"


OnboardingStatus = Literal[
    "NOT_STARTED", "DRAFT", "PENDING_REVIEW", "NEEDS_INFORMATION", "VERIFIED", "REJECTED"
]


class CertificateOut(BaseModel):
    id: str
    original_filename: str
    size_bytes: int
    sha256: str
    uploaded_at: str


class SubmissionOut(BaseModel):
    revision: int
    submitted_at: str
    snapshot_sha256: str
    certificate_id: str
    claim_contested: bool


class OnboardingOut(BaseModel):
    status: OnboardingStatus
    editable: bool
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
    certificate: CertificateOut | None
    # Another supplier already has an uncontested claim on this number. Submitting is still
    # allowed: the claim is then marked contested and resolved in review.
    udyam_claim_conflict: bool
    missing_for_submission: list[str]
    submitted_at: str | None
    submissions: list[SubmissionOut]
