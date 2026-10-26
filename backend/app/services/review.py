"""Business review (Phase 7C; DECISIONS.md Section 13): queue, manual checks, decisions.

Callers are reviewers (`ReviewerPrincipal`, re-checked on every request). Rules enforced here:

- Transitions come from `app.domain.business_review.TRANSITIONS`; a decision is a guarded
  UPDATE (`status = PENDING_REVIEW AND revision = <the submission's>`) plus an insert into
  `business_reviews`, whose unique `submission_id` makes a second decision impossible.
- No reviewer may check or decide a submission for a supplier they own or that they submitted
  (403 `self_review_forbidden`).
- APPROVED needs at least one recorded check and is refused while another supplier's profile
  with the same Udyam number is approved. Approving makes this supplier's claim the
  uncontested one and marks every other claim on the number contested.
- Checks, check items and decisions are append-only (triggers). Snapshots are never changed:
  a supplier answers NEEDS_INFORMATION with a new submission (`services/onboarding.py`).
- Nothing here changes the supplier's eligibility fields, cases or packs, and nothing claims
  a government verification: a check records what one reviewer saw at a named source.
"""

import base64
import binascii
import hashlib
import json
import uuid
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.domain.business_review import (
    OFFICIAL_SOURCES,
    Actor,
    CheckResult,
    CheckSource,
    RecordedCheck,
    ReviewStatus,
    allowed_transitions,
    evidence_level,
)
from app.errors import (
    BadRequest,
    Conflict,
    FieldError,
    Forbidden,
    IntegrityFailed,
    NotFound,
    ValidationFailed,
)
from app.models import (
    BusinessCertificate,
    BusinessCheck,
    BusinessCheckItem,
    BusinessProfile,
    BusinessReview,
    BusinessSubmission,
    Supplier,
    UdyamClaim,
    User,
)
from app.schemas import review as schemas
from app.services.auth import ReviewerPrincipal
from app.storage.business_store import BusinessDocumentStore

QUEUE_LIMIT_MAX = 100
SELF_REVIEW = "You cannot review a business you own or submitted. Ask another reviewer."
NOT_FOUND = "Submission not found."
ALREADY_DECIDED = "This submission has already been decided. Decisions cannot be changed."
NEEDS_CHECK = "Record at least one manual check of this submission before approving it."
ALREADY_APPROVED = "Another supplier's business profile with this Udyam number is already approved."


def _uuid() -> str:
    return str(uuid.uuid4())


def _person(session: Session, user_id: str) -> schemas.PersonOut:
    user = session.get(User, user_id)
    assert user is not None  # foreign key
    return schemas.PersonOut(id=user.id, full_name=user.full_name, email=user.email)


def _submission(session: Session, submission_id: str) -> BusinessSubmission:
    row = session.get(BusinessSubmission, submission_id)
    if row is None:
        raise NotFound(NOT_FOUND)
    return row


def _is_own(session: Session, reviewer: ReviewerPrincipal, row: BusinessSubmission) -> bool:
    supplier = session.get(Supplier, row.supplier_id)
    owner = supplier.owner_user_id if supplier is not None else None
    return reviewer.user_id in (owner, row.submitted_by_user_id)


def _forbid_self_review(
    session: Session, reviewer: ReviewerPrincipal, row: BusinessSubmission
) -> None:
    if _is_own(session, reviewer, row):
        raise Forbidden(SELF_REVIEW, code="self_review_forbidden")


def _review_of(session: Session, submission_id: str) -> BusinessReview | None:
    return session.scalars(
        select(BusinessReview).where(BusinessReview.submission_id == submission_id)
    ).first()


def _status(review: BusinessReview | None) -> schemas.SubmissionStatus:
    # Every undecided submission is the supplier's current one: a supplier can submit again
    # only after a NEEDS_INFORMATION decision.
    return cast(schemas.SubmissionStatus, review.decision if review else "PENDING_REVIEW")


def _snapshot(row: BusinessSubmission) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(row.snapshot)
    return data


# ------------------------------------------------------------------------- queue


def _encode_cursor(submitted_at: str, submission_id: str) -> str:
    raw = json.dumps([submitted_at, submission_id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        submitted_at, submission_id = json.loads(base64.urlsafe_b64decode(padded))
        if not isinstance(submitted_at, str) or not isinstance(submission_id, str):
            raise ValueError
        return submitted_at, submission_id
    except (ValueError, TypeError, binascii.Error):
        raise BadRequest("The cursor is not valid.", code="invalid_cursor") from None


def queue(
    session: Session,
    reviewer: ReviewerPrincipal,
    *,
    status: schemas.SubmissionStatus | None,
    limit: int,
    cursor: str | None,
) -> schemas.QueuePageOut:
    """Submissions with the given status (None = all), oldest first, cursor-paginated."""
    limit = max(1, min(limit, QUEUE_LIMIT_MAX))
    query = select(BusinessSubmission, BusinessReview).outerjoin(
        BusinessReview, BusinessReview.submission_id == BusinessSubmission.id
    )
    if status == "PENDING_REVIEW":
        query = query.where(BusinessReview.id.is_(None))
    elif status is not None:
        query = query.where(BusinessReview.decision == status)
    if cursor:
        after_at, after_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                BusinessSubmission.submitted_at > after_at,
                and_(
                    BusinessSubmission.submitted_at == after_at,
                    BusinessSubmission.id > after_id,
                ),
            )
        )
    query = query.order_by(BusinessSubmission.submitted_at, BusinessSubmission.id).limit(limit + 1)
    with session.begin():
        rows = session.execute(query).all()
        items = [_queue_item(session, reviewer, sub, review) for sub, review in rows[:limit]]
    next_cursor = (
        _encode_cursor(rows[limit - 1][0].submitted_at, rows[limit - 1][0].id)
        if len(rows) > limit
        else None
    )
    return schemas.QueuePageOut(items=items, next_cursor=next_cursor)


def _other_claimants(session: Session, row: BusinessSubmission) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(UdyamClaim)
            .where(
                UdyamClaim.udyam_number == row.udyam_number,
                UdyamClaim.supplier_id != row.supplier_id,
            )
        )
        or 0
    )


def _queue_item(
    session: Session,
    reviewer: ReviewerPrincipal,
    row: BusinessSubmission,
    review: BusinessReview | None,
) -> schemas.QueueItemOut:
    checks = session.scalar(
        select(func.count()).select_from(BusinessCheck).where(BusinessCheck.submission_id == row.id)
    )
    return schemas.QueueItemOut(
        submission_id=row.id,
        supplier_id=row.supplier_id,
        revision=row.revision,
        enterprise_name=_snapshot(row)["profile"].get("enterprise_name"),
        udyam_number=row.udyam_number,
        submitted_at=row.submitted_at,
        status=_status(review),
        claim_contested=row.claim_contested,
        other_claimants=_other_claimants(session, row),
        checks_recorded=checks or 0,
        own_submission=_is_own(session, reviewer, row),
    )


# ------------------------------------------------------------------------ detail


def _checks(session: Session, submission_id: str) -> list[schemas.CheckOut]:
    out = []
    for check in session.scalars(
        select(BusinessCheck)
        .where(BusinessCheck.submission_id == submission_id)
        .order_by(BusinessCheck.recorded_at, BusinessCheck.id)
    ):
        items = session.scalars(
            select(BusinessCheckItem)
            .where(BusinessCheckItem.check_id == check.id)
            .order_by(BusinessCheckItem.field)
        )
        out.append(
            schemas.CheckOut(
                id=check.id,
                reviewer=_person(session, check.reviewer_user_id),
                source=CheckSource(check.source),
                official_source=CheckSource(check.source) in OFFICIAL_SOURCES,
                source_detail=check.source_detail,
                checked_on=check.checked_on,
                recorded_at=check.recorded_at,
                note=check.note,
                items=[
                    schemas.CheckItemOut(
                        field=cast(schemas.CheckField, item.field),
                        submitted_value=item.submitted_value,
                        observed_value=item.observed_value,
                        result=CheckResult(item.result),
                    )
                    for item in items
                ],
            )
        )
    return out


def _decision_out(session: Session, review: BusinessReview, revision: int) -> schemas.DecisionOut:
    return schemas.DecisionOut(
        id=review.id,
        submission_id=review.submission_id,
        revision=revision,
        decision=cast(schemas.Decision, review.decision),
        reason=review.reason,
        internal_note=review.internal_note,
        reviewer=_person(session, review.reviewer_user_id),
        decided_at=review.decided_at,
    )


def _other_claims(session: Session, row: BusinessSubmission) -> list[schemas.OtherClaimOut]:
    out = []
    for claim in session.scalars(
        select(UdyamClaim)
        .where(
            UdyamClaim.udyam_number == row.udyam_number,
            UdyamClaim.supplier_id != row.supplier_id,
        )
        .order_by(UdyamClaim.first_submitted_at, UdyamClaim.id)
    ):
        latest = session.scalars(
            select(BusinessSubmission)
            .where(
                BusinessSubmission.supplier_id == claim.supplier_id,
                BusinessSubmission.udyam_number == row.udyam_number,
            )
            .order_by(BusinessSubmission.revision.desc())
        ).first()
        profile = session.scalars(
            select(BusinessProfile).where(BusinessProfile.supplier_id == claim.supplier_id)
        ).first()
        out.append(
            schemas.OtherClaimOut(
                supplier_id=claim.supplier_id,
                submission_id=latest.id if latest else None,
                enterprise_name=_snapshot(latest)["profile"].get("enterprise_name")
                if latest
                else None,
                profile_status=profile.status if profile else "NOT_STARTED",
                contested=claim.contested,
            )
        )
    return out


def _approval_blockers(
    session: Session, row: BusinessSubmission, checks: Sequence[schemas.CheckOut]
) -> list[str]:
    blockers = []
    if not checks:
        blockers.append(NEEDS_CHECK)
    approved_elsewhere = session.scalars(
        select(BusinessProfile.id).where(
            BusinessProfile.udyam_number == row.udyam_number,
            BusinessProfile.supplier_id != row.supplier_id,
            BusinessProfile.status == ReviewStatus.APPROVED.value,
        )
    ).first()
    if approved_elsewhere is not None:
        blockers.append(ALREADY_APPROVED)
    return blockers


def _profile_status(session: Session, supplier_id: str) -> str:
    profile = session.scalars(
        select(BusinessProfile).where(BusinessProfile.supplier_id == supplier_id)
    ).first()
    assert profile is not None  # a submission implies a profile
    return profile.status


def _history(session: Session, supplier_id: str) -> list[schemas.HistoryItemOut]:
    out = []
    for sub in session.scalars(
        select(BusinessSubmission)
        .where(BusinessSubmission.supplier_id == supplier_id)
        .order_by(BusinessSubmission.revision.desc())
    ):
        review = _review_of(session, sub.id)
        out.append(
            schemas.HistoryItemOut(
                submission_id=sub.id,
                revision=sub.revision,
                submitted_at=sub.submitted_at,
                snapshot_sha256=sub.snapshot_sha256,
                status=_status(review),
                decision=_decision_out(session, review, sub.revision) if review else None,
            )
        )
    return out


def _detail(
    session: Session,
    store: BusinessDocumentStore,
    reviewer: ReviewerPrincipal,
    row: BusinessSubmission,
) -> schemas.ReviewDetailOut:
    snapshot = _snapshot(row)
    certificate = session.get(BusinessCertificate, row.certificate_id)
    assert certificate is not None  # foreign key
    checks = _checks(session, row.id)
    review = _review_of(session, row.id)
    own = _is_own(session, reviewer, row)
    profile_status = _profile_status(session, row.supplier_id)
    allowed: list[schemas.Decision] = []
    if review is None and not own:
        allowed = sorted(
            cast(schemas.Decision, s.value)
            for s in allowed_transitions(Actor.REVIEWER, ReviewStatus(profile_status))
        )
    blockers = _approval_blockers(session, row, checks)
    if blockers and "APPROVED" in allowed:
        allowed.remove("APPROVED")
    return schemas.ReviewDetailOut(
        submission_id=row.id,
        supplier_id=row.supplier_id,
        revision=row.revision,
        status=_status(review),
        profile_status=profile_status,
        submitted_at=row.submitted_at,
        submitted_by=_person(session, row.submitted_by_user_id),
        snapshot_sha256=row.snapshot_sha256,
        snapshot_intact=hashlib.sha256(row.snapshot.encode("utf-8")).hexdigest()
        == row.snapshot_sha256,
        notice=snapshot.get("notice", ""),
        profile=schemas.SubmittedProfileOut.model_validate(snapshot["profile"]),
        certificate=schemas.ReviewCertificateOut(
            id=certificate.id,
            original_filename=certificate.original_filename,
            size_bytes=certificate.size_bytes,
            sha256=certificate.sha256,
            uploaded_at=certificate.uploaded_at,
            bytes_intact=store.current_sha256(certificate.storage_key) == certificate.sha256,
        ),
        claim_contested=row.claim_contested,
        other_claims=_other_claims(session, row),
        checks=checks,
        evidence_level=evidence_level(
            RecordedCheck(source=c.source, results={item.field: item.result for item in c.items})
            for c in checks
        ),
        decision=_decision_out(session, review, row.revision) if review else None,
        own_submission=own,
        allowed_decisions=allowed,
        approval_blockers=blockers if review is None else [],
        history=_history(session, row.supplier_id),
    )


def detail(
    session: Session,
    store: BusinessDocumentStore,
    reviewer: ReviewerPrincipal,
    submission_id: str,
) -> schemas.ReviewDetailOut:
    with session.begin():
        return _detail(session, store, reviewer, _submission(session, submission_id))


def certificate_file(
    session: Session, store: BusinessDocumentStore, submission_id: str
) -> tuple[BusinessCertificate, bytes]:
    """The certificate frozen in a submission (any reviewer may read it, including their own)."""
    with session.begin():
        row = _submission(session, submission_id)
        certificate = session.get(BusinessCertificate, row.certificate_id)
        assert certificate is not None  # foreign key
    content = store.read(certificate.storage_key)
    if content is None:
        raise IntegrityFailed("The stored certificate is missing.", code="integrity_failed")
    return certificate, content


# ------------------------------------------------------------------------ writes


def _submitted_value(profile: dict[str, Any], field: str) -> str | None:
    if field == "address":
        parts = [
            profile.get(key)
            for key in ("address_line1", "address_line2", "city", "state", "pin_code")
        ]
        return ", ".join(str(p) for p in parts if p) or None
    value = profile.get(field)
    return None if value is None else str(value)


def record_check(
    session: Session,
    clock: Clock,
    store: BusinessDocumentStore,
    reviewer: ReviewerPrincipal,
    submission_id: str,
    data: schemas.CheckIn,
) -> schemas.ReviewDetailOut:
    """Record a manual check of an undecided submission (append-only)."""
    if data.checked_on > clock.today():
        raise ValidationFailed(
            errors=[
                FieldError("checked_on", "in_future", "The check date cannot be in the future.")
            ]
        )
    with session.begin():
        row = _submission(session, submission_id)
        _forbid_self_review(session, reviewer, row)
        if _review_of(session, row.id) is not None:
            raise Conflict(ALREADY_DECIDED, code="invalid_transition")
        profile = _snapshot(row)["profile"]
        check_id = _uuid()
        session.add(
            BusinessCheck(
                id=check_id,
                submission_id=row.id,
                supplier_id=row.supplier_id,
                reviewer_user_id=reviewer.user_id,
                source=data.source.value,
                source_detail=data.source_detail,
                checked_on=data.checked_on,
                note=data.note,
                recorded_at=format_utc_timestamp(clock.now_utc()),
            )
        )
        session.flush()
        for item in data.items:
            session.add(
                BusinessCheckItem(
                    id=_uuid(),
                    check_id=check_id,
                    field=item.field,
                    submitted_value=_submitted_value(profile, item.field),
                    observed_value=item.observed_value,
                    result=item.result.value,
                )
            )
        session.flush()
        return _detail(session, store, reviewer, row)


def decide(
    session: Session,
    clock: Clock,
    store: BusinessDocumentStore,
    reviewer: ReviewerPrincipal,
    submission_id: str,
    data: schemas.DecisionIn,
) -> schemas.ReviewDetailOut:
    """Approve, reject or request information on a pending submission. Final and recorded."""
    target = ReviewStatus(data.decision)
    try:
        with session.begin():
            row = _submission(session, submission_id)
            _forbid_self_review(session, reviewer, row)
            now = format_utc_timestamp(clock.now_utc())
            # Guarded write first: it takes SQLite's write lock, so of two concurrent
            # decisions exactly one sees PENDING_REVIEW for this revision.
            result = session.execute(
                update(BusinessProfile)
                .where(
                    BusinessProfile.supplier_id == row.supplier_id,
                    BusinessProfile.revision == row.revision,
                    BusinessProfile.status.in_(
                        [
                            s.value
                            for s in ReviewStatus
                            if target in allowed_transitions(Actor.REVIEWER, s)
                        ]
                    ),
                )
                .values(status=target.value, status_changed_at=now, updated_at=now)
                .execution_options(synchronize_session=False)
            )
            if cast(CursorResult[Any], result).rowcount != 1:
                raise Conflict(ALREADY_DECIDED, code="invalid_transition")
            if target is ReviewStatus.APPROVED:
                blockers = _approval_blockers(session, row, _checks(session, row.id))
                if blockers:  # raising rolls the status change back
                    raise Conflict(" ".join(blockers), code="approval_blocked")
                _resolve_claims(session, row)
            session.add(
                BusinessReview(
                    id=_uuid(),
                    submission_id=row.id,
                    supplier_id=row.supplier_id,
                    reviewer_user_id=reviewer.user_id,
                    decision=target.value,
                    reason=data.reason,
                    internal_note=data.internal_note,
                    decided_at=now,
                )
            )
            session.flush()
            return _detail(session, store, reviewer, row)
    except IntegrityError:  # backstop: the unique submission_id; the guarded UPDATE serialises
        raise Conflict(ALREADY_DECIDED, code="invalid_transition") from None


def _resolve_claims(session: Session, row: BusinessSubmission) -> None:
    """Approval settles a duplicate claim: every other supplier's claim on the number becomes
    contested first (the partial unique index allows one uncontested claim), then this one
    becomes the uncontested claim."""
    session.execute(
        update(UdyamClaim)
        .where(
            UdyamClaim.udyam_number == row.udyam_number,
            UdyamClaim.supplier_id != row.supplier_id,
        )
        .values(contested=True)
        .execution_options(synchronize_session=False)
    )
    session.execute(
        update(UdyamClaim)
        .where(
            UdyamClaim.udyam_number == row.udyam_number,
            UdyamClaim.supplier_id == row.supplier_id,
        )
        .values(contested=False)
        .execution_options(synchronize_session=False)
    )
