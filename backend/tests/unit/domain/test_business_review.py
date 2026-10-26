"""Phase 7C: business review transitions and evidence levels (pure domain)."""

import pytest

from app.domain.business_review import (
    DECISIONS,
    Actor,
    CheckResult,
    CheckSource,
    EvidenceLevel,
    RecordedCheck,
    ReviewStatus,
    allowed_transitions,
    evidence_level,
    is_allowed,
    sources_for,
)

S = ReviewStatus
M, X, N = CheckResult.MATCH, CheckResult.MISMATCH, CheckResult.NOT_FOUND


def test_suppliers_only_submit_from_draft_or_needs_information() -> None:
    assert allowed_transitions(Actor.SUPPLIER, S.DRAFT) == {S.PENDING_REVIEW}
    assert allowed_transitions(Actor.SUPPLIER, S.NEEDS_INFORMATION) == {S.PENDING_REVIEW}
    assert sources_for(Actor.SUPPLIER, S.PENDING_REVIEW) == {S.DRAFT, S.NEEDS_INFORMATION}
    for status in (S.PENDING_REVIEW, S.APPROVED, S.REJECTED):
        assert allowed_transitions(Actor.SUPPLIER, status) == frozenset()


def test_suppliers_can_never_reach_a_decision() -> None:
    for status in S:
        for decision in DECISIONS:
            assert not is_allowed(Actor.SUPPLIER, status, decision)
    assert sources_for(Actor.SUPPLIER, S.APPROVED) == frozenset()


def test_reviewers_decide_only_pending_submissions() -> None:
    assert allowed_transitions(Actor.REVIEWER, S.PENDING_REVIEW) == DECISIONS
    assert {S.APPROVED, S.REJECTED, S.NEEDS_INFORMATION} == DECISIONS
    for status in (S.DRAFT, S.NEEDS_INFORMATION, S.APPROVED, S.REJECTED):
        assert allowed_transitions(Actor.REVIEWER, status) == frozenset()
    assert sources_for(Actor.REVIEWER, S.APPROVED) == {S.PENDING_REVIEW}


@pytest.mark.parametrize("final", [S.APPROVED, S.REJECTED])
def test_approved_and_rejected_are_final(final: ReviewStatus) -> None:
    for actor in Actor:
        for target in S:
            assert not is_allowed(actor, final, target)


def test_reviewers_cannot_submit_for_a_supplier() -> None:
    assert not is_allowed(Actor.REVIEWER, S.DRAFT, S.PENDING_REVIEW)


def test_no_checks_means_supplier_submitted() -> None:
    assert evidence_level([]) is EvidenceLevel.SUPPLIER_SUBMITTED


def test_official_source_with_number_and_name_matching_is_corroborated() -> None:
    check = RecordedCheck(
        CheckSource.UDYAM_PORTAL,
        {"udyam_number": M, "enterprise_name": M, "enterprise_class": M},
    )
    assert evidence_level([check]) is EvidenceLevel.OFFICIAL_RECORD_MATCHED
    other = RecordedCheck(
        CheckSource.OTHER_OFFICIAL_RECORD, {"udyam_number": M, "enterprise_name": M}
    )
    assert evidence_level([other]) is EvidenceLevel.OFFICIAL_RECORD_MATCHED


@pytest.mark.parametrize(
    "check",
    [
        # Not an official source, even when everything matches.
        RecordedCheck(CheckSource.CERTIFICATE_ONLY, {"udyam_number": M, "enterprise_name": M}),
        RecordedCheck(CheckSource.OTHER, {"udyam_number": M, "enterprise_name": M}),
        # Official, but a required field was not compared.
        RecordedCheck(CheckSource.UDYAM_PORTAL, {"udyam_number": M}),
        # Official, but something mismatched or was not found.
        RecordedCheck(
            CheckSource.UDYAM_PORTAL, {"udyam_number": M, "enterprise_name": M, "address": X}
        ),
        RecordedCheck(CheckSource.UDYAM_PORTAL, {"udyam_number": N, "enterprise_name": M}),
    ],
)
def test_anything_less_is_only_manually_reviewed(check: RecordedCheck) -> None:
    assert evidence_level([check]) is EvidenceLevel.MANUALLY_REVIEWED


def test_one_corroborating_check_among_several_is_enough() -> None:
    weak = RecordedCheck(CheckSource.CERTIFICATE_ONLY, {"udyam_number": M})
    strong = RecordedCheck(CheckSource.UDYAM_PORTAL, {"udyam_number": M, "enterprise_name": M})
    assert evidence_level([weak, strong]) is EvidenceLevel.OFFICIAL_RECORD_MATCHED
    assert evidence_level([weak, weak]) is EvidenceLevel.MANUALLY_REVIEWED
