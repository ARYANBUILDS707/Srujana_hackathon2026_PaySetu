"""Business onboarding (Phase 7B): drafts, certificate upload, submission for review.

State machine (server-side only):

    NOT_STARTED (no row) --save draft / upload--> DRAFT --submit--> PENDING_REVIEW
    NEEDS_INFORMATION --edit, submit--> PENDING_REVIEW        (NEEDS_INFORMATION: reviewer only)
    APPROVED, REJECTED                                         (reviewer only, final)

The supplier transitions come from `app.domain.business_review.TRANSITIONS`. Suppliers can
write only while the status is DRAFT or NEEDS_INFORMATION. Every write starts with a
conditional UPDATE guarded by that status, so a draft edit racing a submission cannot change
submitted data, and two simultaneous submissions produce exactly one revision. No code path
here sets APPROVED, REJECTED or NEEDS_INFORMATION (`services/review.py` does). Answering
NEEDS_INFORMATION creates a new submission; earlier snapshots are never changed.

Nothing here changes the supplier's eligibility fields, cases or evidence packs.
"""

import hashlib
import uuid
from collections.abc import Iterable
from datetime import date
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.domain.business_review import Actor, ReviewStatus, sources_for
from app.domain.integrity import canonical_json
from app.errors import Conflict, FieldError, IntegrityFailed, NotFound, ValidationFailed
from app.models import (
    BusinessCertificate,
    BusinessProfile,
    BusinessReview,
    BusinessSubmission,
    UdyamClaim,
)
from app.schemas import onboarding as schemas
from app.storage.business_store import BusinessDocumentStore

EDITABLE = tuple(sorted(s.value for s in sources_for(Actor.SUPPLIER, ReviewStatus.PENDING_REVIEW)))
# Reasons the supplier may read; an approval's reason and every internal note stay with reviewers.
REASON_VISIBLE = ("NEEDS_INFORMATION", "REJECTED")
SNAPSHOT_SCHEMA = "paysetu.business-submission.v1"
SELF_DECLARED_NOTICE = (
    "Self-declared by the supplier. PaySetu has not verified the Udyam registration, the "
    "enterprise classification or the certificate. A SHA-256 records the uploaded bytes; it "
    "does not show that the certificate is genuine."
)

DRAFT_FIELDS = (
    "enterprise_name",
    "udyam_number",
    "enterprise_class",
    "registration_date",
    "address_line1",
    "address_line2",
    "city",
    "state",
    "pin_code",
    "contact_email",
    "contact_phone",
    "representative_name",
    "representative_role",
    "authorisation_note",
    "authority_confirmed",
)
REQUIRED_FOR_SUBMISSION = {
    "enterprise_name": "Enter the registered enterprise name.",
    "udyam_number": "Enter the Udyam Registration Number.",
    "enterprise_class": "Choose the enterprise classification.",
    "address_line1": "Enter the registered address.",
    "city": "Enter the city or town.",
    "state": "Enter the state.",
    "pin_code": "Enter the PIN code.",
    "contact_email": "Enter a business contact email.",
    "representative_name": "Enter the representative's name.",
    "representative_role": "Choose the representative's role.",
    "authority_confirmed": "Confirm that you are authorised to act for this enterprise.",
    "certificate": "Upload the Udyam certificate (PDF).",
}
LOCKED_MESSAGE = (
    "These details have been submitted for review and can no longer be edited. "
    "If something is wrong, wait for the reviewer's request for information."
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _profile(session: Session, supplier_id: str) -> BusinessProfile | None:
    return session.scalars(
        select(BusinessProfile).where(BusinessProfile.supplier_id == supplier_id)
    ).first()


def _draft_values(data: schemas.DraftIn) -> dict[str, Any]:
    values = data.model_dump()
    for key in ("enterprise_class", "representative_role"):
        if values[key] is not None:
            values[key] = str(values[key].value)
    return {key: values[key] for key in DRAFT_FIELDS}


def _missing(profile: BusinessProfile) -> list[str]:
    missing = [
        field
        for field in REQUIRED_FOR_SUBMISSION
        if field != "certificate" and not getattr(profile, field)
    ]
    if profile.certificate_id is None:
        missing.append("certificate")
    return missing


def _claim_conflict(session: Session, supplier_id: str, udyam_number: str | None) -> bool:
    if not udyam_number:
        return False
    other = session.scalars(
        select(UdyamClaim).where(
            UdyamClaim.udyam_number == udyam_number,
            UdyamClaim.supplier_id != supplier_id,
            UdyamClaim.contested.is_(False),
        )
    ).first()
    return other is not None


def _certificate_out(row: BusinessCertificate | None) -> schemas.CertificateOut | None:
    if row is None:
        return None
    return schemas.CertificateOut(
        id=row.id,
        original_filename=row.original_filename,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        uploaded_at=row.uploaded_at,
    )


def _outcome(review: BusinessReview | None) -> schemas.ReviewOutcomeOut | None:
    if review is None:
        return None
    return schemas.ReviewOutcomeOut(
        decision=cast(schemas.ReviewDecision, review.decision),
        reason=review.reason if review.decision in REASON_VISIBLE else None,
        decided_at=review.decided_at,
    )


def _out(session: Session, supplier_id: str) -> schemas.OnboardingOut:
    profile = _profile(session, supplier_id)
    reviews = {
        r.submission_id: r
        for r in session.scalars(
            select(BusinessReview).where(BusinessReview.supplier_id == supplier_id)
        )
    }
    history = [
        schemas.SubmissionOut(
            id=s.id,
            revision=s.revision,
            submitted_at=s.submitted_at,
            snapshot_sha256=s.snapshot_sha256,
            certificate_id=s.certificate_id,
            claim_contested=s.claim_contested,
            review=_outcome(reviews.get(s.id)),
        )
        for s in session.scalars(
            select(BusinessSubmission)
            .where(BusinessSubmission.supplier_id == supplier_id)
            .order_by(BusinessSubmission.revision.desc())
        )
    ]
    latest_review = history[0].review if history else None
    if profile is None:
        empty: dict[str, Any] = {field: None for field in DRAFT_FIELDS}
        empty["authority_confirmed"] = False
        return schemas.OnboardingOut(
            status="NOT_STARTED",
            editable=True,
            certificate=None,
            udyam_claim_conflict=False,
            missing_for_submission=list(REQUIRED_FOR_SUBMISSION),
            submitted_at=None,
            latest_review=latest_review,
            submissions=history,
            **empty,
        )
    certificate = (
        session.get(BusinessCertificate, profile.certificate_id) if profile.certificate_id else None
    )
    return schemas.OnboardingOut(
        status=cast(schemas.OnboardingStatus, profile.status),
        editable=profile.status in EDITABLE,
        certificate=_certificate_out(certificate),
        udyam_claim_conflict=_claim_conflict(session, supplier_id, profile.udyam_number),
        missing_for_submission=_missing(profile),
        submitted_at=profile.submitted_at,
        latest_review=latest_review,
        submissions=history,
        **{field: getattr(profile, field) for field in DRAFT_FIELDS},
    )


def get_onboarding(session: Session, supplier_id: str) -> schemas.OnboardingOut:
    with session.begin():
        return _out(session, supplier_id)


def _write_or_create(session: Session, supplier_id: str, now: str, values: dict[str, Any]) -> None:
    """Apply `values` to an editable profile, creating a DRAFT if there is none yet.

    The guarded UPDATE is the transaction's first statement (it takes SQLite's write lock),
    so the status check and the write cannot be separated by a concurrent submission.
    """
    result = session.execute(
        update(BusinessProfile)
        .where(BusinessProfile.supplier_id == supplier_id, BusinessProfile.status.in_(EDITABLE))
        .values(**values, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[Any], result).rowcount == 1:
        return
    if _profile(session, supplier_id) is not None:
        raise Conflict(LOCKED_MESSAGE, code="onboarding_locked")
    defaults: dict[str, Any] = {field: None for field in DRAFT_FIELDS}
    defaults["authority_confirmed"] = False
    defaults["certificate_id"] = None
    session.add(
        BusinessProfile(
            id=_uuid(),
            supplier_id=supplier_id,
            status="DRAFT",
            revision=0,
            submitted_at=None,
            status_changed_at=now,
            created_at=now,
            updated_at=now,
            **{**defaults, **values},
        )
    )
    session.flush()


def save_draft(
    session: Session, clock: Clock, supplier_id: str, data: schemas.DraftIn
) -> schemas.OnboardingOut:
    if data.registration_date is not None and data.registration_date > clock.today():
        raise ValidationFailed(
            errors=[
                FieldError(
                    "registration_date",
                    "in_future",
                    "The registration date cannot be in the future.",
                )
            ]
        )
    try:
        with session.begin():
            _write_or_create(
                session, supplier_id, format_utc_timestamp(clock.now_utc()), _draft_values(data)
            )
    except IntegrityError:  # two first saves raced: the profile exists now, so update it
        with session.begin():
            _write_or_create(
                session, supplier_id, format_utc_timestamp(clock.now_utc()), _draft_values(data)
            )
    return get_onboarding(session, supplier_id)


def _ensure_editable(session: Session, supplier_id: str) -> None:
    with session.begin():
        profile = _profile(session, supplier_id)
        if profile is not None and profile.status not in EDITABLE:
            raise Conflict(LOCKED_MESSAGE, code="onboarding_locked")


def upload_certificate(
    session: Session,
    clock: Clock,
    store: BusinessDocumentStore,
    supplier_id: str,
    user_id: str,
    *,
    filename: str,
    chunks: Iterable[bytes],
    max_bytes: int,
) -> schemas.OnboardingOut:
    """Store a certificate PDF and make it the draft's certificate (replacing any earlier
    draft certificate, whose row and bytes are kept: submitted snapshots may refer to them)."""
    _ensure_editable(session, supplier_id)  # refuse before accepting any bytes
    stored = store.save_pdf(supplier_id, chunks, max_bytes=max_bytes)
    now = format_utc_timestamp(clock.now_utc())
    certificate_id = _uuid()
    with session.begin():
        # The guarded profile write comes first; the certificate row follows in the same
        # transaction, so a locked profile leaves no new row behind.
        _write_or_create(session, supplier_id, now, {"certificate_id": None})
        session.add(
            BusinessCertificate(
                id=certificate_id,
                supplier_id=supplier_id,
                original_filename=_display_filename(filename),
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_key=stored.storage_key,
                uploaded_at=now,
                uploaded_by_user_id=user_id,
            )
        )
        session.flush()
        session.execute(
            update(BusinessProfile)
            .where(BusinessProfile.supplier_id == supplier_id)
            .values(certificate_id=certificate_id, updated_at=now)
            .execution_options(synchronize_session=False)
        )
    return get_onboarding(session, supplier_id)


def _display_filename(filename: str) -> str:
    """Display only; never used in storage paths."""
    name = "".join(ch for ch in filename.replace("\\", "/").split("/")[-1] if ch.isprintable())
    return (name or "certificate.pdf")[:255]


def certificate_file(
    session: Session, store: BusinessDocumentStore, supplier_id: str, certificate_id: str
) -> tuple[BusinessCertificate, str]:
    with session.begin():
        row = session.scalars(
            select(BusinessCertificate).where(
                BusinessCertificate.id == certificate_id,
                BusinessCertificate.supplier_id == supplier_id,
            )
        ).first()
        if row is None:
            raise NotFound("Certificate not found or you don't have access.")
        return row, str(store.path_for(row.storage_key))


def _claim(session: Session, supplier_id: str, udyam_number: str, now: str) -> bool:
    """Record this supplier's claim on the number; return whether it is contested."""
    existing = session.scalars(
        select(UdyamClaim).where(
            UdyamClaim.supplier_id == supplier_id, UdyamClaim.udyam_number == udyam_number
        )
    ).first()
    if existing is not None:
        return existing.contested
    try:
        with session.begin_nested():  # savepoint: the partial unique index decides
            session.add(
                UdyamClaim(
                    id=_uuid(),
                    supplier_id=supplier_id,
                    udyam_number=udyam_number,
                    contested=False,
                    first_submitted_at=now,
                )
            )
        return False
    except IntegrityError:  # someone else holds the uncontested claim: send both to review
        session.add(
            UdyamClaim(
                id=_uuid(),
                supplier_id=supplier_id,
                udyam_number=udyam_number,
                contested=True,
                first_submitted_at=now,
            )
        )
        session.flush()
        return True


def submit(
    session: Session,
    clock: Clock,
    store: BusinessDocumentStore,
    supplier_id: str,
    user_id: str,
) -> schemas.OnboardingOut:
    with session.begin():
        now = format_utc_timestamp(clock.now_utc())
        result = session.execute(
            update(BusinessProfile)
            .where(BusinessProfile.supplier_id == supplier_id, BusinessProfile.status.in_(EDITABLE))
            .values(
                status="PENDING_REVIEW",
                revision=BusinessProfile.revision + 1,
                submitted_at=now,
                status_changed_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        profile = _profile(session, supplier_id)
        if cast(CursorResult[Any], result).rowcount != 1:
            if profile is None:
                raise ValidationFailed(
                    "Save your business details before submitting.",
                    errors=[
                        FieldError(f, "required", m) for f, m in REQUIRED_FOR_SUBMISSION.items()
                    ],
                )
            raise Conflict(LOCKED_MESSAGE, code="onboarding_locked")
        assert profile is not None
        session.refresh(profile)
        missing = _missing(profile)
        if missing:  # raising rolls the status change back
            raise ValidationFailed(
                "Some required details are missing.",
                errors=[FieldError(f, "required", REQUIRED_FOR_SUBMISSION[f]) for f in missing],
            )
        certificate = session.get(BusinessCertificate, profile.certificate_id)
        assert certificate is not None and profile.udyam_number is not None
        if store.current_sha256(certificate.storage_key) != certificate.sha256:
            raise IntegrityFailed(
                "The stored certificate no longer matches its recorded hash. Upload it again.",
                code="integrity_failed",
            )
        contested = _claim(session, supplier_id, profile.udyam_number, now)
        snapshot = {
            "schema": SNAPSHOT_SCHEMA,
            "revision": profile.revision,
            "supplier_id": supplier_id,
            "submitted_at": now,
            "submitted_by_user_id": user_id,
            "status_on_submission": "PENDING_REVIEW",
            "notice": SELF_DECLARED_NOTICE,
            "profile": {
                field: (value.isoformat() if isinstance(value, date) else value)
                for field in DRAFT_FIELDS
                for value in [getattr(profile, field)]
            },
            "certificate": {
                "id": certificate.id,
                "sha256": certificate.sha256,
                "size_bytes": certificate.size_bytes,
                "original_filename": certificate.original_filename,
                "uploaded_at": certificate.uploaded_at,
            },
            "udyam_claim": {"number": profile.udyam_number, "contested": contested},
        }
        encoded = canonical_json(snapshot)
        session.add(
            BusinessSubmission(
                id=_uuid(),
                supplier_id=supplier_id,
                revision=profile.revision,
                udyam_number=profile.udyam_number,
                certificate_id=certificate.id,
                claim_contested=contested,
                snapshot=encoded.decode("utf-8"),
                snapshot_sha256=hashlib.sha256(encoded).hexdigest(),
                submitted_at=now,
                submitted_by_user_id=user_id,
            )
        )
        session.flush()
        return _out(session, supplier_id)


def submissions(session: Session, supplier_id: str) -> list[schemas.SubmissionOut]:
    with session.begin():
        return _out(session, supplier_id).submissions
