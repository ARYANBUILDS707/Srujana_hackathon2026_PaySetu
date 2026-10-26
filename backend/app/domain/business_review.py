"""Business review status transitions and evidence levels (Phase 7C; DECISIONS.md Section 13).

Pure: no I/O. Services enforce these tables; nothing else decides which status may follow
which.

    supplier:  DRAFT             --submit-->  PENDING_REVIEW
               NEEDS_INFORMATION --submit-->  PENDING_REVIEW   (a new, separate submission)
    reviewer:  PENDING_REVIEW    --decide-->  APPROVED | REJECTED | NEEDS_INFORMATION

APPROVED and REJECTED are final: no actor can move a profile out of them. "APPROVED" records a
reviewer's decision after a manual check; it is never a government verification.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum


class Actor(StrEnum):
    SUPPLIER = "supplier"
    REVIEWER = "reviewer"


class ReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


DECISIONS = frozenset(
    {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.NEEDS_INFORMATION}
)

TRANSITIONS: Mapping[tuple[Actor, ReviewStatus], frozenset[ReviewStatus]] = {
    (Actor.SUPPLIER, ReviewStatus.DRAFT): frozenset({ReviewStatus.PENDING_REVIEW}),
    (Actor.SUPPLIER, ReviewStatus.NEEDS_INFORMATION): frozenset({ReviewStatus.PENDING_REVIEW}),
    (Actor.REVIEWER, ReviewStatus.PENDING_REVIEW): DECISIONS,
}


def allowed_transitions(actor: Actor, current: ReviewStatus) -> frozenset[ReviewStatus]:
    """The statuses `actor` may move a profile to from `current` (empty when none)."""
    return TRANSITIONS.get((actor, current), frozenset())


def is_allowed(actor: Actor, current: ReviewStatus, target: ReviewStatus) -> bool:
    return target in allowed_transitions(actor, current)


def sources_for(actor: Actor, target: ReviewStatus) -> frozenset[ReviewStatus]:
    """Every status from which `actor` may reach `target` (the supplier's editable statuses)."""
    return frozenset(
        current
        for (who, current), targets in TRANSITIONS.items()
        if who is actor and target in targets
    )


class CheckSource(StrEnum):
    """Where a reviewer looked. Only the first two are official records."""

    UDYAM_PORTAL = "udyam_portal"  # the reviewer looked the number up manually
    OTHER_OFFICIAL_RECORD = "other_official_record"
    CERTIFICATE_ONLY = "certificate_only"  # only the uploaded PDF was examined
    OTHER = "other"


OFFICIAL_SOURCES = frozenset({CheckSource.UDYAM_PORTAL, CheckSource.OTHER_OFFICIAL_RECORD})


class CheckResult(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"


# Fields that must match an official record before the details count as corroborated.
CORROBORATION_FIELDS = frozenset({"udyam_number", "enterprise_name"})


class EvidenceLevel(StrEnum):
    SUPPLIER_SUBMITTED = "supplier_submitted"  # no check recorded
    MANUALLY_REVIEWED = "manually_reviewed"  # checked, but not corroborated officially
    OFFICIAL_RECORD_MATCHED = "official_record_matched"


@dataclass(frozen=True)
class RecordedCheck:
    source: CheckSource
    results: Mapping[str, CheckResult]  # field -> result


def evidence_level(checks: Iterable[RecordedCheck]) -> EvidenceLevel:
    """How well the submitted details are supported by the recorded manual checks.

    OFFICIAL_RECORD_MATCHED needs one check against an official source in which every
    CORROBORATION_FIELDS entry matched and no field mismatched or was not found. Any other
    recorded check gives MANUALLY_REVIEWED; none gives SUPPLIER_SUBMITTED.
    """
    level = EvidenceLevel.SUPPLIER_SUBMITTED
    for check in checks:
        level = EvidenceLevel.MANUALLY_REVIEWED
        if check.source not in OFFICIAL_SOURCES:
            continue
        all_match = all(result is CheckResult.MATCH for result in check.results.values())
        if all_match and check.results.keys() >= CORROBORATION_FIELDS:
            return EvidenceLevel.OFFICIAL_RECORD_MATCHED
    return level
