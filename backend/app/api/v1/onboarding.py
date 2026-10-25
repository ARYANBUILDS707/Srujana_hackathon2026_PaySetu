"""Business onboarding endpoints (Phase 7B; DECISIONS.md Section 11).

Every route needs a signed-in supplier (`PrincipalDep`) and acts
only on that supplier's own profile, certificates and submissions (another supplier's IDs
answer 404). Owner, reviewer and status fields cannot be sent: `DraftIn` forbids unknown
fields, and no route accepts a status. Mounted with the other supplier routes (not in
production while the evaluation build lasts).
"""

from collections.abc import Iterator
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import ClockDep, LimiterDep, PrincipalDep, SessionDep, SettingsDep
from app.schemas import onboarding as schemas
from app.security.body_limit import MIB
from app.security.rate_limit import RateLimitCategory
from app.services import onboarding as service
from app.storage.business_store import BusinessDocumentStore

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _store(request: Request) -> BusinessDocumentStore:
    store: BusinessDocumentStore = request.app.state.business_store
    return store


StoreDep = Annotated[BusinessDocumentStore, Depends(_store)]


@router.get("", response_model=schemas.OnboardingOut)
def get_onboarding(principal: PrincipalDep, session: SessionDep) -> schemas.OnboardingOut:
    """The signed-in supplier's onboarding profile, status and submission history."""
    return service.get_onboarding(session, principal.supplier_id)


@router.put("/draft", response_model=schemas.OnboardingOut)
def save_draft(
    data: schemas.DraftIn, principal: PrincipalDep, session: SessionDep, clock: ClockDep
) -> schemas.OnboardingOut:
    """Create or replace the draft (only while DRAFT or NEEDS_INFORMATION; else 409)."""
    return service.save_draft(session, clock, principal.supplier_id, data)


@router.post("/certificate", response_model=schemas.OnboardingOut, status_code=201)
def upload_certificate(
    principal: PrincipalDep,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
    store: StoreDep,
    file: Annotated[UploadFile, File()],
) -> schemas.OnboardingOut:
    """Upload (or replace) the draft's Udyam certificate. PDF only, size-limited."""
    limiter.hit(RateLimitCategory.CERTIFICATE_UPLOAD, principal.user_id)
    return service.upload_certificate(
        session,
        clock,
        store,
        principal.supplier_id,
        principal.user_id,
        filename=file.filename or "certificate.pdf",
        chunks=_chunks(file.file),
        max_bytes=settings.business_certificate_max_mb * MIB,
    )


def _chunks(handle: BinaryIO) -> Iterator[bytes]:
    while chunk := handle.read(1024 * 1024):
        yield chunk


@router.get("/certificates/{certificate_id}/download")
def download_certificate(
    certificate_id: str, principal: PrincipalDep, session: SessionDep, store: StoreDep
) -> FileResponse:
    """The original certificate bytes, as an attachment, to its owner only."""
    row, path = service.certificate_file(session, store, principal.supplier_id, certificate_id)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox",
            "X-PaySetu-SHA256": row.sha256,
        },
    )


@router.post("/submit", response_model=schemas.OnboardingOut)
def submit(
    principal: PrincipalDep, session: SessionDep, clock: ClockDep, store: StoreDep
) -> schemas.OnboardingOut:
    """Submit for review: PENDING_REVIEW plus an immutable snapshot. Never verifies."""
    return service.submit(session, clock, store, principal.supplier_id, principal.user_id)


@router.get("/submissions", response_model=list[schemas.SubmissionOut])
def submissions(principal: PrincipalDep, session: SessionDep) -> list[schemas.SubmissionOut]:
    """Submission history, newest first."""
    return service.submissions(session, principal.supplier_id)
