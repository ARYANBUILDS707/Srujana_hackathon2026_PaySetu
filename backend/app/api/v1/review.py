"""Business review endpoints (Phase 7C; DECISIONS.md Section 13).

Every route needs an active reviewer grant (`ReviewerDep`: 401 signed out, 403
`reviewer_required` otherwise); a supplier session can never reach them. The reviewer is always
the session's user: no payload names a reviewer, supplier, status or submitted value (unknown
fields → 422). Mounted with the onboarding routes (not in production while the evaluation
build lasts).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import ClockDep, LimiterDep, ReviewerDep, SessionDep
from app.api.downloads import attachment
from app.schemas import review as schemas
from app.security.rate_limit import RateLimitCategory
from app.services import review as service
from app.storage.business_store import BusinessDocumentStore

router = APIRouter(prefix="/review", tags=["review"])


def _store(request: Request) -> BusinessDocumentStore:
    store: BusinessDocumentStore = request.app.state.business_store
    return store


StoreDep = Annotated[BusinessDocumentStore, Depends(_store)]
StatusFilter = schemas.SubmissionStatus | None


@router.get("/submissions", response_model=schemas.QueuePageOut)
def queue(
    reviewer: ReviewerDep,
    session: SessionDep,
    status: Annotated[StatusFilter, Query()] = "PENDING_REVIEW",
    all_statuses: Annotated[bool, Query(alias="all")] = False,
    limit: Annotated[int, Query(ge=1, le=service.QUEUE_LIMIT_MAX)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> schemas.QueuePageOut:
    """Submissions oldest first: pending by default, `?status=` to filter, `?all=true` for all."""
    return service.queue(
        session,
        reviewer,
        status=None if all_statuses else status,
        limit=limit,
        cursor=cursor,
    )


@router.get("/submissions/{submission_id}", response_model=schemas.ReviewDetailOut)
def detail(
    submission_id: str, reviewer: ReviewerDep, session: SessionDep, store: StoreDep
) -> schemas.ReviewDetailOut:
    """The frozen snapshot, certificate integrity, duplicate claims, checks and history."""
    return service.detail(session, store, reviewer, submission_id)


@router.get("/submissions/{submission_id}/certificate")
def download_certificate(
    submission_id: str, reviewer: ReviewerDep, session: SessionDep, store: StoreDep
) -> Response:
    """The submission's certificate, as an attachment (never rendered inline)."""
    row, content = service.certificate_file(session, store, submission_id)
    return attachment(
        content,
        media_type="application/pdf",
        filename=row.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox",
            "X-PaySetu-SHA256": row.sha256,
        },
    )


@router.post(
    "/submissions/{submission_id}/checks", response_model=schemas.ReviewDetailOut, status_code=201
)
def record_check(
    submission_id: str,
    data: schemas.CheckIn,
    reviewer: ReviewerDep,
    session: SessionDep,
    clock: ClockDep,
    limiter: LimiterDep,
    store: StoreDep,
) -> schemas.ReviewDetailOut:
    """Record a manual check: source, what was compared, the result and the date."""
    limiter.hit(RateLimitCategory.REVIEW_WRITE, reviewer.user_id)
    return service.record_check(session, clock, store, reviewer, submission_id, data)


@router.post("/submissions/{submission_id}/decision", response_model=schemas.ReviewDetailOut)
def decide(
    submission_id: str,
    data: schemas.DecisionIn,
    reviewer: ReviewerDep,
    session: SessionDep,
    clock: ClockDep,
    limiter: LimiterDep,
    store: StoreDep,
) -> schemas.ReviewDetailOut:
    """Approve, reject or request information. Final: 409 once decided."""
    limiter.hit(RateLimitCategory.REVIEW_WRITE, reviewer.user_id)
    return service.decide(session, clock, store, reviewer, submission_id, data)
