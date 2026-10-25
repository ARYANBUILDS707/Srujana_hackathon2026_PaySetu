"""Phase 7B: business onboarding drafts, certificate uploads, submission and Udyam claims."""

import hashlib
import json
import stat
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DatabaseError

from app.clock import FrozenClock, format_utc_timestamp
from app.config import Settings
from app.db import Database
from app.errors import Conflict
from app.main import create_app
from app.models import BusinessCertificate, BusinessProfile, BusinessSubmission, UdyamClaim
from app.schemas.onboarding import DraftIn, normalise_udyam
from app.services import onboarding as service
from app.storage.business_store import BusinessDocumentStore
from seed.demo import seed
from tests.auth_helpers import CSRF, sign_in_as_demo, signup, verify_email

UDYAM = "UDYAM-MH-12-0001234"
FULL_DRAFT: dict[str, Any] = {
    "enterprise_name": "Sample Fasteners (TEST)",
    "udyam_number": "udyam mh 12 0001234",
    "enterprise_class": "micro",
    "registration_date": "2024-06-12",
    "address_line1": "Plot 7, Sample Industrial Estate",
    "address_line2": None,
    "city": "Pune",
    "state": "Maharashtra",
    "pin_code": "411 001",
    "contact_email": "Accounts@Sample.example",
    "contact_phone": "+91 98765 43210",
    "representative_name": "Sample Proprietor",
    "representative_role": "proprietor",
    "authorisation_note": "Sole proprietor (sample)",
    "authority_confirmed": True,
}


def pdf(label: str = "a", extra: bytes = b"") -> bytes:
    """A minimal structurally valid PDF; `label` makes the bytes unique."""
    return (
        b"%PDF-1.4\n% SAMPLE certificate " + label.encode() + b", not a real document\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n" + extra + b"xref\n0 3\n"
        b"trailer<</Root 1 0 R/Size 3>>\nstartxref\n9\n%%EOF\n"
    )


@pytest.fixture
def ob_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(
        update={"database_url": migrated_database_url, "business_certificate_max_mb": 1}
    )


@pytest.fixture
def app(ob_settings: Settings, frozen_clock: FrozenClock) -> Any:
    return create_app(ob_settings, clock=frozen_clock)


def _verified_client(app: Any, settings: Settings, email: str) -> TestClient:
    client = TestClient(app)
    assert signup(client, email).status_code == 201
    verify_email(client, settings, email)
    return client


@pytest.fixture
def client(app: Any, ob_settings: Settings) -> TestClient:
    return _verified_client(app, ob_settings, "owner@example.com")


@pytest.fixture
def other(app: Any, ob_settings: Settings) -> TestClient:
    return _verified_client(app, ob_settings, "other@example.com")


@pytest.fixture
def db(ob_settings: Settings) -> Iterator[Database]:
    database = Database(ob_settings.database_url)
    try:
        yield database
    finally:
        database.dispose()


def _get(client: TestClient) -> Any:
    return client.get("/api/v1/onboarding")


def _save(client: TestClient, **changes: Any) -> Any:
    return client.put("/api/v1/onboarding/draft", json={**FULL_DRAFT, **changes}, headers=CSRF)


def _upload(client: TestClient, content: bytes, name: str = "udyam.pdf") -> Any:
    return client.post(
        "/api/v1/onboarding/certificate",
        files={"file": (name, content, "application/octet-stream")},
        headers=CSRF,
    )


def _submit(client: TestClient) -> Any:
    return client.post("/api/v1/onboarding/submit", headers=CSRF)


def _ready(client: TestClient, label: str = "a", **changes: Any) -> None:
    assert _save(client, **changes).status_code == 200
    assert _upload(client, pdf(label)).status_code == 201


# ------------------------------------------------------------------------ drafts


def test_a_new_supplier_has_not_started(client: TestClient) -> None:
    body = _get(client).json()
    assert body["status"] == "NOT_STARTED" and body["editable"] is True
    assert body["certificate"] is None and body["submissions"] == []
    assert "certificate" in body["missing_for_submission"]


def test_save_and_resume_a_draft_with_normalised_values(client: TestClient) -> None:
    saved = _save(client)
    assert saved.status_code == 200
    body = _get(client).json()  # resume later
    assert body["status"] == "DRAFT" and body["editable"] is True
    assert body["udyam_number"] == UDYAM
    assert body["pin_code"] == "411001"
    assert body["contact_phone"] == "+919876543210"
    assert body["contact_email"] == "accounts@sample.example"
    assert body["enterprise_class"] == "micro" and body["registration_date"] == "2024-06-12"
    assert body["missing_for_submission"] == ["certificate"]

    # PUT replaces the whole draft: omitted fields are cleared.
    partial = client.put(
        "/api/v1/onboarding/draft", json={"enterprise_name": "Renamed (TEST)"}, headers=CSRF
    )
    assert partial.json()["enterprise_name"] == "Renamed (TEST)"
    assert partial.json()["udyam_number"] is None
    assert "udyam_number" in partial.json()["missing_for_submission"]


@pytest.mark.parametrize(
    "value",
    [
        "UDYAM-MH-12-000123",
        "UDYAM-M1-12-0001234",
        "UDYAM-MH-1A-0001234",
        "MH-12-0001234",
        "UDYAMMH120001234X",
        "UAM-MH-12-0001234",
    ],
)
def test_invalid_udyam_formats_are_rejected_with_guidance(client: TestClient, value: str) -> None:
    response = _save(client, udyam_number=value)
    assert response.status_code == 422
    errors = {e["field"]: e["message"] for e in response.json()["errors"]}
    assert errors["udyam_number"].startswith("Enter the Udyam Registration Number as")
    assert "UDYAM-XX-00-0000000" in errors["udyam_number"]
    assert value not in response.text  # submitted values are never echoed


@pytest.mark.parametrize(
    ("raw", "normalised"),
    [
        ("UDYAM-MH-12-0001234", UDYAM),
        ("udyam-mh-12-0001234", UDYAM),
        (" UDYAM MH 12 0001234 ", UDYAM),
        ("UDYAMMH120001234", UDYAM),
        ("udyam/mh/12/0001234", UDYAM),
    ],
)
def test_udyam_numbers_are_normalised(raw: str, normalised: str) -> None:
    assert normalise_udyam(raw) == normalised


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pin_code", "011001"),
        ("pin_code", "41100"),
        ("contact_phone", "12345"),
        ("contact_phone", "+1 555 0100 222"),
        ("contact_email", "not-an-email"),
        ("enterprise_class", "large"),
        ("representative_role", "ceo"),
        ("enterprise_name", "x" * 201),
    ],
)
def test_other_fields_are_validated(client: TestClient, field: str, value: str) -> None:
    response = _save(client, **{field: value})
    assert response.status_code == 422
    assert field in {e["field"] for e in response.json()["errors"]}


def test_registration_date_cannot_be_in_the_future(client: TestClient) -> None:
    # Frozen "today" is 1 Nov 2026.
    response = _save(client, registration_date="2026-11-02")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "registration_date"
    assert _save(client, registration_date="2026-11-01").status_code == 200


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "supplier_id",
        "owner_user_id",
        "reviewer_id",
        "verified",
        "certificate_id",
        "revision",
        "submitted_at",
    ],
)
def test_clients_cannot_set_status_owner_or_reviewer_fields(
    client: TestClient, db: Database, field: str
) -> None:
    response = _save(client, **{field: "VERIFIED"})
    assert response.status_code == 422
    with db.session() as session:
        assert session.scalars(select(BusinessProfile)).first() is None


# ------------------------------------------------------------------- certificates


def test_certificate_upload_is_private_hashed_and_downloadable_by_its_owner(
    client: TestClient, ob_settings: Settings, db: Database
) -> None:
    content = pdf("owner")
    response = _upload(client, content, "../../My Udyam Certificate.pdf")
    assert response.status_code == 201
    certificate = response.json()["certificate"]
    assert certificate["sha256"] == hashlib.sha256(content).hexdigest()
    assert certificate["size_bytes"] == len(content)
    assert certificate["original_filename"] == "My Udyam Certificate.pdf"  # display only
    assert response.json()["status"] == "DRAFT"  # an upload starts a draft

    with db.session() as session:
        row = session.scalars(select(BusinessCertificate)).one()
    stored = Path(ob_settings.storage_dir) / "business" / row.storage_key
    assert row.storage_key.startswith("certificates/") and row.storage_key.endswith(row.sha256)
    assert ".." not in row.storage_key and "Udyam" not in row.storage_key
    assert stored.read_bytes() == content
    assert stat.S_IMODE(stored.stat().st_mode) == 0o600
    assert not (Path(ob_settings.storage_dir) / "evidence").exists()  # not the Evidence Vault

    download = client.get(f"/api/v1/onboarding/certificates/{certificate['id']}/download")
    assert download.status_code == 200 and download.content == content
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["cache-control"] == "private, no-store"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-security-policy"] == "sandbox"


@pytest.mark.parametrize(
    ("content", "status", "code"),
    [
        (b"\x89PNG\r\n\x1a\n not a pdf", 415, "not_a_pdf"),
        (b"MZ executable pretending", 415, "not_a_pdf"),
        (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n", 415, "damaged_pdf"),
        (b"%PDF-1.4\nxref\ntrailer<<>>\nstartxref\n9\n%%EOF\n", 415, "damaged_pdf"),
        (
            pdf("js", b"3 0 obj<</S/JavaScript/JS(app.alert(1))>>endobj\n"),
            415,
            "pdf_active_content",
        ),
        (pdf("launch", b"3 0 obj<</S/Launch/F(cmd.exe)>>endobj\n"), 415, "pdf_active_content"),
        (pdf("embed", b"3 0 obj<</Type/EmbeddedFile>>endobj\n"), 415, "pdf_active_content"),
        (b"", 415, "unsupported_file_type"),
    ],
    ids=["png", "exe", "no-eof", "no-catalog", "javascript", "launch", "embedded", "empty"],
)
def test_invalid_pdfs_are_rejected_and_nothing_is_kept(
    client: TestClient, ob_settings: Settings, db: Database, content: bytes, status: int, code: str
) -> None:
    response = _upload(client, content, "udyam.pdf")
    assert response.status_code == status and response.json()["code"] == code
    with db.session() as session:
        assert session.scalars(select(BusinessCertificate)).first() is None
    folder = Path(ob_settings.storage_dir) / "business" / "certificates"
    assert not folder.exists() or not any(p.is_file() for p in folder.rglob("*"))


def test_oversized_certificates_are_rejected(client: TestClient, db: Database) -> None:
    padding = b"% " + b"x" * (1024 * 1024) + b"\n"  # limit is 1 MB in this fixture
    response = _upload(client, pdf("big", padding))
    assert response.status_code == 413 and response.json()["code"] == "file_too_large"
    with db.session() as session:
        assert session.scalars(select(BusinessCertificate)).first() is None


def test_replacing_a_draft_certificate_keeps_the_old_one(client: TestClient, db: Database) -> None:
    first = _upload(client, pdf("first")).json()["certificate"]
    second = _upload(client, pdf("second")).json()["certificate"]
    assert first["id"] != second["id"]
    assert _get(client).json()["certificate"]["id"] == second["id"]
    with db.session() as session:
        assert len(session.scalars(select(BusinessCertificate)).all()) == 2  # nothing deleted
    old = client.get(f"/api/v1/onboarding/certificates/{first['id']}/download")
    assert old.status_code == 200  # still the owner's document


def test_certificate_uploads_are_rate_limited(client: TestClient) -> None:
    codes = [_upload(client, pdf(f"n{n}")).status_code for n in range(21)]
    assert codes == [201] * 20 + [429]


# ------------------------------------------------------------------- submission


def test_submission_needs_every_required_detail(client: TestClient) -> None:
    empty = _submit(client)
    assert empty.status_code == 422  # nothing saved yet
    _save(client, enterprise_name=None, representative_role=None, authority_confirmed=False)
    response = _submit(client)
    assert response.status_code == 422
    fields = {e["field"] for e in response.json()["errors"]}
    assert fields == {
        "enterprise_name",
        "representative_role",
        "authority_confirmed",
        "certificate",
    }
    assert _get(client).json()["status"] == "DRAFT"  # rolled back


def test_submission_moves_to_pending_review_with_an_immutable_snapshot(
    client: TestClient, db: Database
) -> None:
    _ready(client)
    response = _submit(client)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING_REVIEW" and body["editable"] is False
    assert body["submitted_at"] and len(body["submissions"]) == 1
    summary = body["submissions"][0]
    assert summary["revision"] == 1 and summary["claim_contested"] is False

    with db.session() as session:
        row = session.scalars(select(BusinessSubmission)).one()
    assert hashlib.sha256(row.snapshot.encode()).hexdigest() == row.snapshot_sha256
    assert summary["snapshot_sha256"] == row.snapshot_sha256
    snapshot = json.loads(row.snapshot)
    assert snapshot["profile"]["udyam_number"] == UDYAM
    assert snapshot["certificate"]["sha256"] == hashlib.sha256(pdf()).hexdigest()
    assert snapshot["status_on_submission"] == "PENDING_REVIEW"
    assert "has not verified" in snapshot["notice"]

    history = client.get("/api/v1/onboarding/submissions")
    assert history.status_code == 200 and history.json() == body["submissions"]


def test_submitted_information_cannot_be_edited(client: TestClient, db: Database) -> None:
    _ready(client)
    _submit(client)
    for response in (
        _save(client, enterprise_name="Changed after submission"),
        _upload(client, pdf("late")),
        _submit(client),
    ):
        assert response.status_code == 409 and response.json()["code"] == "onboarding_locked"
    body = _get(client).json()
    assert body["enterprise_name"] == "Sample Fasteners (TEST)"
    assert body["status"] == "PENDING_REVIEW"
    with db.session() as session:
        assert len(session.scalars(select(BusinessSubmission)).all()) == 1
        assert len(session.scalars(select(BusinessCertificate)).all()) == 1


def test_no_supplier_route_can_reach_verified(app: Any, client: TestClient) -> None:
    operations = sorted(
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        if path.startswith("/api/v1/onboarding")
        for method in ops
    )
    assert operations == [
        ("GET", "/api/v1/onboarding"),
        ("GET", "/api/v1/onboarding/certificates/{certificate_id}/download"),
        ("GET", "/api/v1/onboarding/submissions"),
        ("POST", "/api/v1/onboarding/certificate"),
        ("POST", "/api/v1/onboarding/submit"),
        ("PUT", "/api/v1/onboarding/draft"),
    ]
    _ready(client)
    assert _submit(client).json()["status"] == "PENDING_REVIEW"  # never further
    for path in ("/api/v1/onboarding/verify", "/api/v1/onboarding/approve"):
        assert client.post(path, headers=CSRF).status_code in (404, 405)


def test_snapshots_and_certificates_are_protected_in_the_database(
    client: TestClient, db: Database
) -> None:
    _ready(client)
    _submit(client)
    with db.session() as session:
        for statement in (
            "UPDATE business_submissions SET claim_contested = 1",
            "DELETE FROM business_submissions",
            "UPDATE business_certificates SET sha256 = 'x'",
            "DELETE FROM business_certificates",
            "DELETE FROM udyam_claims",
            "UPDATE udyam_claims SET udyam_number = 'UDYAM-XX-00-0000000'",
        ):
            with pytest.raises(DatabaseError), session.begin():
                session.execute(text(statement))


def test_a_changed_certificate_file_blocks_submission(
    client: TestClient, ob_settings: Settings, db: Database
) -> None:
    _ready(client)
    with db.session() as session:
        key = session.scalars(select(BusinessCertificate)).one().storage_key
    stored = Path(ob_settings.storage_dir) / "business" / key
    stored.chmod(0o600)
    stored.write_bytes(stored.read_bytes() + b"tampered")
    response = _submit(client)
    assert response.status_code == 409 and response.json()["code"] == "integrity_failed"
    assert _get(client).json()["status"] == "DRAFT"


def test_concurrent_submissions_create_exactly_one_revision(
    client: TestClient, ob_settings: Settings, frozen_clock: FrozenClock, db: Database
) -> None:
    _ready(client)
    with db.session() as session:
        supplier_id = session.scalars(select(BusinessProfile)).one().supplier_id
        user_id = session.scalars(select(BusinessCertificate)).one().uploaded_by_user_id
    store = BusinessDocumentStore(Path(ob_settings.storage_dir))
    barrier = threading.Barrier(4)
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        database = Database(ob_settings.database_url)
        try:
            barrier.wait()
            with database.session() as session:
                service.submit(session, frozen_clock, store, supplier_id, user_id)
            result = "ok"
        except Conflict:
            result = "locked"
        finally:
            database.dispose()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["locked", "locked", "locked", "ok"]
    with db.session() as session:
        assert len(session.scalars(select(BusinessSubmission)).all()) == 1


# --------------------------------------------------------------- duplicate claims


def test_a_second_claim_on_the_same_number_goes_to_review_as_contested(
    client: TestClient, other: TestClient, db: Database
) -> None:
    _ready(client, "first")
    assert _submit(client).json()["submissions"][0]["claim_contested"] is False

    _ready(other, "second")
    assert _get(other).json()["udyam_claim_conflict"] is True  # warned before submitting
    contested = _submit(other)
    assert contested.status_code == 200 and contested.json()["status"] == "PENDING_REVIEW"
    assert contested.json()["submissions"][0]["claim_contested"] is True

    with db.session() as session:
        claims = session.scalars(select(UdyamClaim)).all()
    assert sorted(c.contested for c in claims) == [False, True]
    assert all(c.udyam_number == UDYAM for c in claims)
    assert _get(client).json()["udyam_claim_conflict"] is False  # the first holder is not warned


def test_concurrent_claims_on_one_number_leave_exactly_one_uncontested(
    app: Any, ob_settings: Settings, frozen_clock: FrozenClock, db: Database
) -> None:
    clients = [_verified_client(app, ob_settings, f"racer{n}@example.com") for n in range(3)]
    for n, racer in enumerate(clients):
        _ready(racer, f"racer{n}")
    with db.session() as session:
        targets = [
            (p.supplier_id, c.uploaded_by_user_id)
            for p in session.scalars(select(BusinessProfile))
            for c in [session.get(BusinessCertificate, p.certificate_id)]
            if c is not None
        ]
    store = BusinessDocumentStore(Path(ob_settings.storage_dir))
    barrier = threading.Barrier(len(targets))
    errors: list[BaseException] = []

    def attempt(supplier_id: str, user_id: str) -> None:
        database = Database(ob_settings.database_url)
        try:
            barrier.wait()
            with database.session() as session:
                service.submit(session, frozen_clock, store, supplier_id, user_id)
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)
        finally:
            database.dispose()

    threads = [threading.Thread(target=attempt, args=t) for t in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    with db.session() as session:
        claims = session.scalars(select(UdyamClaim)).all()
        statuses = {p.status for p in session.scalars(select(BusinessProfile))}
    assert len(claims) == 3 and sum(not c.contested for c in claims) == 1
    assert statuses == {"PENDING_REVIEW"}


# -------------------------------------------------------------------- isolation


def test_suppliers_cannot_see_or_touch_each_others_onboarding(
    client: TestClient, other: TestClient
) -> None:
    _ready(client, "mine")
    certificate_id = _get(client).json()["certificate"]["id"]
    assert (
        other.get(f"/api/v1/onboarding/certificates/{certificate_id}/download").status_code == 404
    )
    assert _get(other).json()["status"] == "NOT_STARTED"
    _save(other, enterprise_name="Other (TEST)")
    assert _get(client).json()["enterprise_name"] == "Sample Fasteners (TEST)"


def test_onboarding_needs_a_session_and_a_verified_email(app: Any, ob_settings: Settings) -> None:
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/v1/onboarding").status_code == 401
        assert signup(anonymous, "unverified@example.com").status_code == 201
        response = anonymous.get("/api/v1/onboarding")
        assert response.status_code == 403 and response.json()["code"] == "email_not_verified"
        assert _upload(anonymous, pdf()).status_code == 403


def test_writes_need_csrf_headers(client: TestClient) -> None:
    assert client.put("/api/v1/onboarding/draft", json={}).status_code == 403
    assert client.post("/api/v1/onboarding/submit").status_code == 403


# ---------------------------------------------------------- existing accounts


def test_existing_suppliers_keep_their_workspace_and_eligibility(
    ob_settings: Settings, frozen_clock: FrozenClock
) -> None:
    db = Database(ob_settings.database_url)
    try:
        with db.session() as session:
            seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    finally:
        db.dispose()
    with TestClient(create_app(ob_settings, clock=frozen_clock)) as demo:
        sign_in_as_demo(demo, ob_settings, frozen_clock)
        assert _get(demo).json()["status"] == "NOT_STARTED"  # never migrated to VERIFIED
        before = demo.get("/api/v1/supplier").json()
        assert demo.get("/api/v1/cases").status_code == 200  # no business check needed
        _ready(demo, "demo", udyam_number="UDYAM-TS-00-0000000")
        _submit(demo)
        after = demo.get("/api/v1/supplier").json()
        assert after == before  # eligibility comes from the supplier profile, unchanged
        assert demo.get("/api/v1/cases").status_code == 200


def test_migration_gives_existing_suppliers_no_onboarding_row(migrated_database_url: str) -> None:
    engine = create_engine(migrated_database_url)
    try:
        with engine.connect() as connection:
            count = connection.execute(text("SELECT count(*) FROM business_profiles")).scalar_one()
    finally:
        engine.dispose()
    assert count == 0


def test_draft_schema_forbids_unknown_fields() -> None:
    with pytest.raises(ValueError):
        DraftIn.model_validate({"status": "VERIFIED"})
