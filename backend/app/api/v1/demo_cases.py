"""Supplier case endpoints of the evaluation build (API.md Sections 2.3–2.10, subset).

Every route requires a signed-in supplier (`PrincipalDep`, Phase 6) and passes the session's
supplier ID to the services, which scope every query by it: another supplier's case, buyer,
response or evidence answers 404. IDs in paths and bodies are never trusted for ownership.

This router is still mounted only when APP_ENV is not `production` (see app.main): the legal
rules behind these results await advocate review (DECISIONS.md LR-01 to LR-25) and the evidence
pack is labelled as an evaluation export. CSRF, body limits, security headers and error
formats apply as for every API route.
"""

from collections.abc import Iterator
from datetime import date
from typing import IO, Annotated, BinaryIO

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import ClockDep, LimiterDep, PrincipalDep, SessionDep, SettingsDep
from app.api.downloads import attachment
from app.domain.types import EvidenceKind
from app.schemas import cases as schemas
from app.security.rate_limit import RateLimitCategory
from app.services import cases as service
from app.services import pack as pack_service
from app.storage.evidence_store import EvidenceStore

router = APIRouter(tags=["demo"])


def _store(request: Request) -> EvidenceStore:
    store: EvidenceStore = request.app.state.evidence_store
    return store


StoreDep = Annotated[EvidenceStore, Depends(_store)]


@router.get("/supplier", response_model=schemas.SupplierOut)
def get_supplier(principal: PrincipalDep, session: SessionDep) -> schemas.SupplierOut:
    return service.get_supplier(session, principal.supplier_id)


@router.get("/buyers", response_model=list[schemas.BuyerOut])
def list_buyers(principal: PrincipalDep, session: SessionDep) -> list[schemas.BuyerOut]:
    return service.list_buyers(session, principal.supplier_id)


@router.post("/buyers", response_model=schemas.BuyerOut, status_code=201)
def create_buyer(
    principal: PrincipalDep, data: schemas.BuyerCreate, session: SessionDep, clock: ClockDep
) -> schemas.BuyerOut:
    return service.create_buyer(session, principal.supplier_id, clock, data)


@router.get("/cases", response_model=list[schemas.CaseSummaryOut])
def list_cases(
    principal: PrincipalDep,
    session: SessionDep,
    clock: ClockDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.CaseSummaryOut]:
    return service.list_cases(session, principal.supplier_id, clock, limit)


@router.post("/cases", response_model=schemas.CaseOut, status_code=201)
def create_case(
    principal: PrincipalDep, data: schemas.CaseCreate, session: SessionDep, clock: ClockDep
) -> schemas.CaseOut:
    return service.create_case(session, principal.supplier_id, clock, data)


@router.get("/cases/{case_id}", response_model=schemas.CaseOut)
def get_case(
    principal: PrincipalDep, case_id: str, session: SessionDep, clock: ClockDep
) -> schemas.CaseOut:
    return service.get_case(session, principal.supplier_id, clock, case_id)


@router.get("/cases/{case_id}/checklist", response_model=schemas.ChecklistOut)
def get_checklist(
    principal: PrincipalDep, case_id: str, session: SessionDep, clock: ClockDep
) -> schemas.ChecklistOut:
    return service.get_checklist(session, principal.supplier_id, clock, case_id)


@router.get("/cases/{case_id}/interest", response_model=schemas.InterestOut)
def get_interest(
    principal: PrincipalDep,
    case_id: str,
    session: SessionDep,
    clock: ClockDep,
    as_of: date | None = None,
) -> schemas.InterestOut:
    return service.get_interest(session, principal.supplier_id, clock, case_id, as_of)


@router.get("/cases/{case_id}/responses", response_model=list[schemas.ResponseOut])
def list_responses(
    principal: PrincipalDep, case_id: str, session: SessionDep, clock: ClockDep
) -> list[schemas.ResponseOut]:
    return service.list_responses(session, principal.supplier_id, clock, case_id)


@router.post(
    "/cases/{case_id}/responses", response_model=list[schemas.ResponseOut], status_code=201
)
def record_response(
    principal: PrincipalDep,
    case_id: str,
    data: schemas.ResponseCreate,
    session: SessionDep,
    clock: ClockDep,
) -> list[schemas.ResponseOut]:
    return service.record_response(session, principal.supplier_id, clock, case_id, data)


@router.post(
    "/cases/{case_id}/responses/{response_id}/remove-objection",
    response_model=list[schemas.ResponseOut],
)
def remove_objection(
    principal: PrincipalDep,
    case_id: str,
    response_id: str,
    data: schemas.ObjectionRemoval,
    session: SessionDep,
    clock: ClockDep,
) -> list[schemas.ResponseOut]:
    return service.remove_objection(
        session, principal.supplier_id, clock, case_id, response_id, data.removed_on
    )


@router.get("/cases/{case_id}/evidence", response_model=list[schemas.EvidenceOut])
def list_evidence(
    principal: PrincipalDep, case_id: str, session: SessionDep
) -> list[schemas.EvidenceOut]:
    return service.list_evidence(session, principal.supplier_id, case_id)


@router.post("/cases/{case_id}/evidence", response_model=schemas.EvidenceOut, status_code=201)
def upload_evidence(
    principal: PrincipalDep,
    case_id: str,
    limiter: LimiterDep,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    store: StoreDep,
    file: Annotated[UploadFile, File()],
    kind: Annotated[EvidenceKind, Form()],
    note: Annotated[str | None, Form(max_length=500)] = None,
) -> schemas.EvidenceOut:
    limiter.hit(RateLimitCategory.EVIDENCE_UPLOAD, principal.user_id)
    return service.upload_evidence(
        session,
        principal.supplier_id,
        clock,
        settings,
        store,
        case_id,
        kind=kind,
        filename=file.filename or "upload",
        chunks=_chunks(file.file),
        note=note,
    )


def _chunks(handle: BinaryIO) -> Iterator[bytes]:
    while chunk := handle.read(1024 * 1024):
        yield chunk


@router.get("/evidence/{evidence_id}/download")
def download_evidence(
    principal: PrincipalDep, evidence_id: str, session: SessionDep, store: StoreDep
) -> Response:
    item, content = service.evidence_file(session, principal.supplier_id, store, evidence_id)
    return attachment(
        content,
        media_type=item.mime_type,
        filename=item.original_filename,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/cases/{case_id}/integrity-check", response_model=schemas.IntegrityOut)
def integrity_check(
    principal: PrincipalDep,
    case_id: str,
    session: SessionDep,
    clock: ClockDep,
    store: StoreDep,
) -> schemas.IntegrityOut:
    return service.check_integrity(session, principal.supplier_id, clock, store, case_id)


@router.get("/cases/{case_id}/timeline", response_model=list[schemas.TimelineEventOut])
def timeline(
    principal: PrincipalDep, case_id: str, session: SessionDep
) -> list[schemas.TimelineEventOut]:
    return service.list_timeline(session, principal.supplier_id, case_id)


def _stream_and_close(handle: IO[bytes]) -> Iterator[bytes]:
    try:
        while chunk := handle.read(1024 * 1024):
            yield chunk
    finally:
        handle.close()


@router.get("/cases/{case_id}/evidence-pack")
def download_evidence_pack(
    principal: PrincipalDep,
    case_id: str,
    limiter: LimiterDep,
    session: SessionDep,
    clock: ClockDep,
    store: StoreDep,
) -> StreamingResponse:
    """Build and download the case's evidence pack (ZIP). Read-only; refused if integrity fails."""
    limiter.hit(RateLimitCategory.PACK_GENERATION, f"{principal.supplier_id}|{case_id[:64]}")
    export = pack_service.export_pack(session, principal.supplier_id, clock, store, case_id)
    return StreamingResponse(
        _stream_and_close(export.file),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{export.filename}"',
            "Content-Length": str(export.size_bytes),
            "Cache-Control": "private, no-store",
            "X-PaySetu-Pack-SHA256": export.pack_sha256,
            "Access-Control-Expose-Headers": "X-PaySetu-Pack-SHA256, Content-Disposition",
        },
    )
