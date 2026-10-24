"""Supplier eligibility for MSMED Act Chapter V protections (T2.4; R9, R9a, R10, R11).

The result describes what the recorded facts show. It is not a legal determination: R9a, R10
and R11 are interpretations pending counsel review, and a self-declared or simulated
verification is reported as uncertain evidence, never as proof.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.rules import RuleSet
from app.domain.types import EnterpriseClass, MajorActivity, UdyamVerificationStatus

UDYAM_NUMBER_PATTERN = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")


class EligibilityVerdict(StrEnum):
    ELIGIBLE = "eligible"
    ELIGIBLE_WITH_WARNINGS = "eligible_with_warnings"
    NOT_ELIGIBLE = "not_eligible"
    CANNOT_ASSESS = "cannot_assess"


class ReasonStatus(StrEnum):
    MET = "met"
    WARNING = "warning"
    MISSING = "missing"
    FAILED = "failed"


@dataclass(frozen=True)
class SupplierProfileFacts:
    udyam_number: str | None
    enterprise_class: EnterpriseClass | None
    major_activity: MajorActivity | None
    udyam_registration_date: date | None
    verification_status: UdyamVerificationStatus


@dataclass(frozen=True)
class EligibilityReason:
    code: str
    rule_ids: tuple[str, ...]
    status: ReasonStatus
    message: str


@dataclass(frozen=True)
class EligibilityResult:
    verdict: EligibilityVerdict
    reasons: tuple[EligibilityReason, ...]
    rule_set_version: str
    unconfirmed_rules: tuple[str, ...]


def is_valid_udyam_number(value: str) -> bool:
    return UDYAM_NUMBER_PATTERN.fullmatch(value) is not None


def assess_eligibility(profile: SupplierProfileFacts, rule_set: RuleSet) -> EligibilityResult:
    """Evaluate eligibility from the supplier profile alone (no case-specific facts)."""
    reasons = (
        _udyam_number_reason(profile.udyam_number),
        _class_reason(profile.enterprise_class),
        _activity_reason(profile.major_activity),
        _registration_date_reason(profile.udyam_registration_date),
        _evidence_reason(profile.verification_status),
    )
    by_code = {r.code: r for r in reasons}
    if by_code["enterprise_class"].status is ReasonStatus.FAILED:
        verdict = EligibilityVerdict.NOT_ELIGIBLE
    elif any(
        by_code[code].status in (ReasonStatus.MISSING, ReasonStatus.FAILED)
        for code in ("udyam_number", "enterprise_class")
    ):
        verdict = EligibilityVerdict.CANNOT_ASSESS
    elif any(r.status is not ReasonStatus.MET for r in reasons):
        verdict = EligibilityVerdict.ELIGIBLE_WITH_WARNINGS
    else:
        verdict = EligibilityVerdict.ELIGIBLE

    rule_ids = tuple(dict.fromkeys(i for r in reasons for i in r.rule_ids))
    return EligibilityResult(
        verdict=verdict,
        reasons=reasons,
        rule_set_version=rule_set.version,
        unconfirmed_rules=rule_set.unconfirmed(rule_ids),
    )


def assess_registration_timing(
    registration_date: date | None, delivery_date: date
) -> EligibilityReason:
    """R10: flag a delivery made before the supplier's Udyam registration date."""
    if registration_date is None:
        return EligibilityReason(
            "registered_before_supply",
            ("R10",),
            ReasonStatus.MISSING,
            "Udyam registration date not recorded, so timing against the delivery cannot "
            "be checked.",
        )
    if registration_date <= delivery_date:
        return EligibilityReason(
            "registered_before_supply",
            ("R10",),
            ReasonStatus.MET,
            "Registered on or before the delivery date.",
        )
    return EligibilityReason(
        "registered_before_supply",
        ("R10",),
        ReasonStatus.WARNING,
        "Registered after the delivery date; this may limit the claim. Ask counsel.",
    )


def _udyam_number_reason(value: str | None) -> EligibilityReason:
    rules = ("R9", "R9a")
    if value is None or not value.strip():
        return EligibilityReason(
            "udyam_number", rules, ReasonStatus.MISSING, "Udyam number not recorded."
        )
    if not is_valid_udyam_number(value):
        return EligibilityReason(
            "udyam_number",
            rules,
            ReasonStatus.FAILED,
            "Udyam number is not in the format UDYAM-XX-00-0000000.",
        )
    return EligibilityReason("udyam_number", rules, ReasonStatus.MET, "Udyam number recorded.")


def _class_reason(value: EnterpriseClass | None) -> EligibilityReason:
    rules = ("R9",)
    if value is None:
        return EligibilityReason(
            "enterprise_class", rules, ReasonStatus.MISSING, "Enterprise class not recorded."
        )
    if value is EnterpriseClass.MEDIUM:
        return EligibilityReason(
            "enterprise_class",
            rules,
            ReasonStatus.FAILED,
            "Medium enterprises are not covered by the delayed-payment provisions.",
        )
    return EligibilityReason(
        "enterprise_class", rules, ReasonStatus.MET, f"{value.value.capitalize()} enterprise."
    )


def _activity_reason(value: MajorActivity | None) -> EligibilityReason:
    rules = ("R11",)
    if value is None:
        return EligibilityReason(
            "major_activity", rules, ReasonStatus.MISSING, "Major activity not recorded."
        )
    if value is MajorActivity.TRADING:
        return EligibilityReason(
            "major_activity",
            rules,
            ReasonStatus.WARNING,
            "Trading registrations may not be covered. Ask counsel.",
        )
    return EligibilityReason("major_activity", rules, ReasonStatus.MET, f"Activity: {value.value}.")


def _registration_date_reason(value: date | None) -> EligibilityReason:
    if value is None:
        return EligibilityReason(
            "udyam_registration_date",
            ("R10",),
            ReasonStatus.MISSING,
            "Udyam registration date not recorded.",
        )
    return EligibilityReason(
        "udyam_registration_date",
        ("R10",),
        ReasonStatus.MET,
        f"Registered on {value.isoformat()}.",
    )


def _evidence_reason(value: UdyamVerificationStatus) -> EligibilityReason:
    rules = ("R9a",)
    if value is UdyamVerificationStatus.SELF_DECLARED:
        return EligibilityReason(
            "udyam_evidence",
            rules,
            ReasonStatus.WARNING,
            "Udyam details are self-declared; upload the certificate.",
        )
    if value is UdyamVerificationStatus.PROVIDER_VERIFIED_SANDBOX:
        return EligibilityReason(
            "udyam_evidence",
            rules,
            ReasonStatus.WARNING,
            "Verified only in a sandbox (simulated); not a real registry check.",
        )
    return EligibilityReason("udyam_evidence", rules, ReasonStatus.MET, "Udyam evidence on file.")
