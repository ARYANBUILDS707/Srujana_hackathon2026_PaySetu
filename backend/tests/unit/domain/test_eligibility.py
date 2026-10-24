from dataclasses import replace
from datetime import date

import pytest

from app.domain.eligibility import (
    EligibilityVerdict,
    ReasonStatus,
    SupplierProfileFacts,
    assess_eligibility,
    assess_registration_timing,
    is_valid_udyam_number,
)
from app.domain.rules import RuleSet
from app.domain.types import EnterpriseClass, MajorActivity, UdyamVerificationStatus

COMPLETE = SupplierProfileFacts(
    udyam_number="UDYAM-TS-02-0001234",
    enterprise_class=EnterpriseClass.MICRO,
    major_activity=MajorActivity.MANUFACTURING,
    udyam_registration_date=date(2024, 6, 12),
    verification_status=UdyamVerificationStatus.CERTIFICATE_UPLOADED,
)


def _verdict(profile: SupplierProfileFacts, rule_set: RuleSet) -> EligibilityVerdict:
    return assess_eligibility(profile, rule_set).verdict


def test_complete_evidenced_micro_supplier_is_eligible(rule_set: RuleSet) -> None:
    result = assess_eligibility(COMPLETE, rule_set)
    assert result.verdict is EligibilityVerdict.ELIGIBLE
    assert all(r.status is ReasonStatus.MET for r in result.reasons)
    assert "R9a" in result.unconfirmed_rules


@pytest.mark.parametrize(
    ("change", "verdict"),
    [
        ({"enterprise_class": EnterpriseClass.MEDIUM}, EligibilityVerdict.NOT_ELIGIBLE),
        ({"enterprise_class": EnterpriseClass.SMALL}, EligibilityVerdict.ELIGIBLE),
        ({"udyam_number": None}, EligibilityVerdict.CANNOT_ASSESS),
        ({"udyam_number": "  "}, EligibilityVerdict.CANNOT_ASSESS),
        ({"udyam_number": "UDYAM-TS-2-123"}, EligibilityVerdict.CANNOT_ASSESS),
        ({"enterprise_class": None}, EligibilityVerdict.CANNOT_ASSESS),
        ({"major_activity": MajorActivity.TRADING}, EligibilityVerdict.ELIGIBLE_WITH_WARNINGS),
        ({"major_activity": None}, EligibilityVerdict.ELIGIBLE_WITH_WARNINGS),
        ({"udyam_registration_date": None}, EligibilityVerdict.ELIGIBLE_WITH_WARNINGS),
        (
            {"verification_status": UdyamVerificationStatus.SELF_DECLARED},
            EligibilityVerdict.ELIGIBLE_WITH_WARNINGS,
        ),
        (
            {"verification_status": UdyamVerificationStatus.PROVIDER_VERIFIED_SANDBOX},
            EligibilityVerdict.ELIGIBLE_WITH_WARNINGS,
        ),
        (
            {"verification_status": UdyamVerificationStatus.PROVIDER_VERIFIED_LIVE},
            EligibilityVerdict.ELIGIBLE,
        ),
    ],
)
def test_verdicts(
    change: dict[str, object], verdict: EligibilityVerdict, rule_set: RuleSet
) -> None:
    assert _verdict(replace(COMPLETE, **change), rule_set) is verdict  # type: ignore[arg-type]


def test_medium_class_wins_over_missing_number(rule_set: RuleSet) -> None:
    profile = replace(COMPLETE, udyam_number=None, enterprise_class=EnterpriseClass.MEDIUM)
    assert _verdict(profile, rule_set) is EligibilityVerdict.NOT_ELIGIBLE


def test_sandbox_verification_is_labelled_simulated(rule_set: RuleSet) -> None:
    profile = replace(
        COMPLETE, verification_status=UdyamVerificationStatus.PROVIDER_VERIFIED_SANDBOX
    )
    evidence = [
        r for r in assess_eligibility(profile, rule_set).reasons if r.code == "udyam_evidence"
    ]
    assert "simulated" in evidence[0].message


@pytest.mark.parametrize(
    ("registered", "status"),
    [
        (None, ReasonStatus.MISSING),
        (date(2026, 11, 1), ReasonStatus.MET),  # same day as delivery
        (date(2026, 10, 1), ReasonStatus.MET),
        (date(2026, 11, 2), ReasonStatus.WARNING),
    ],
)
def test_registration_timing(registered: date | None, status: ReasonStatus) -> None:
    assert assess_registration_timing(registered, date(2026, 11, 1)).status is status


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("UDYAM-TS-02-0001234", True),
        ("udyam-ts-02-0001234", False),
        ("UDYAM-TS-02-000123", False),
        ("UDYAM-T5-02-0001234", False),
        ("UDYAM-TS-02-0001234 ", False),
    ],
)
def test_udyam_number_format(value: str, valid: bool) -> None:
    assert is_valid_udyam_number(value) is valid
