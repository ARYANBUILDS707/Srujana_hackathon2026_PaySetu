"""Hosted deployment: uploaded bytes in a private Supabase Storage bucket (STORAGE_BACKEND).

A local fake of the Storage REST API stands in for Supabase (AGENTS.md 11: never call real
external services in tests). It implements the three calls PaySetu makes, with Supabase's
answers: upload (`x-upsert: false`; an existing name answers 400 with statusCode "409"),
authenticated download (a missing object answers 400 with statusCode "404"), and it rejects
any request without the service-role key.
"""

import hashlib
import io
import json
import threading
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.clock import FrozenClock, format_utc_timestamp
from app.config import Settings, StorageBackend, load_settings
from app.db import Database
from app.main import create_app
from app.services import reviewers
from app.storage.blobs import SupabaseBlobs
from seed.demo import seed
from tests.auth_helpers import CSRF, TEST_PASSWORD, login, sign_in_as_demo
from tests.conftest import TEST_SETTINGS
from tests.integration.test_onboarding import FULL_DRAFT, pdf

SERVICE_KEY = "test-only-service-role-key"
BUCKET = "paysetu-private"
EVIDENCE_PDF = b"%PDF-1.4\n% SAMPLE invoice stored in the fake bucket, not real evidence\n"
EML = b"From: buyer@example.invalid\nSubject: Received\n\nGoods received (sample)."


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail = False
        self.requests: list[tuple[str, str, str | None]] = []  # method, path, auth header


def _handler(bucket: FakeBucket) -> type[BaseHTTPRequestHandler]:
    upload_prefix = f"/storage/v1/object/{BUCKET}/"
    read_prefix = f"/storage/v1/object/authenticated/{BUCKET}/"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:  # keep test output quiet
            return

        def _json(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorised(self) -> bool:
            bucket.requests.append((self.command, self.path, self.headers.get("Authorization")))
            if bucket.fail:
                self._json(503, {"error": "unavailable"})
                return False
            ok = self.headers.get("Authorization") == f"Bearer {SERVICE_KEY}" and (
                self.headers.get("apikey") == SERVICE_KEY
            )
            if not ok:
                self._json(400, {"statusCode": "403", "error": "Unauthorized"})
            return ok

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            if not self._authorised():
                return
            if not self.path.startswith(upload_prefix):
                self._json(400, {"statusCode": "404", "error": "Bucket not found"})
                return
            name = unquote(self.path.removeprefix(upload_prefix))
            if name in bucket.objects and self.headers.get("x-upsert") != "true":
                self._json(400, {"statusCode": "409", "error": "Duplicate"})
                return
            bucket.objects[name] = body
            self._json(200, {"Key": f"{BUCKET}/{name}"})

        def do_GET(self) -> None:
            if not self._authorised():
                return
            name = unquote(self.path.removeprefix(read_prefix))
            if not self.path.startswith(read_prefix) or name not in bucket.objects:
                self._json(400, {"statusCode": "404", "error": "not_found"})
                return
            data = bucket.objects[name]
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


@pytest.fixture
def fake_bucket() -> Iterator[tuple[FakeBucket, str]]:
    bucket = FakeBucket()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(bucket))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield bucket, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def hosted_settings(
    settings: Settings, migrated_database_url: str, fake_bucket: tuple[FakeBucket, str]
) -> Settings:
    # model_copy skips validation, which requires https: the fake server is plain http.
    return settings.model_copy(
        update={
            "database_url": migrated_database_url,
            "storage_backend": StorageBackend.SUPABASE,
            "supabase_url": fake_bucket[1],
            "supabase_service_role_key": SecretStr(SERVICE_KEY),
            "supabase_storage_bucket": BUCKET,
        }
    )


@pytest.fixture
def client(hosted_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    db = Database(hosted_settings.database_url)
    try:
        with db.session() as session:
            seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    finally:
        db.dispose()
    with TestClient(create_app(hosted_settings, clock=frozen_clock)) as test_client:
        sign_in_as_demo(test_client, hosted_settings, frozen_clock)
        yield test_client


def _case(client: TestClient) -> str:
    buyer = client.get("/api/v1/buyers").json()[0]["id"]
    body = {
        "buyer_id": buyer,
        "invoice_number": "RF/26-27/201",
        "invoice_date": "2026-10-01",
        "invoice_amount": "500000.00",
        "delivery_date": "2026-10-01",
        "description": "M8 hex bolts (sample)",
        "deal_type": "verbal",
    }
    return str(client.post("/api/v1/cases", json=body, headers=CSRF).json()["id"])


def _upload(client: TestClient, case_id: str, content: bytes, kind: str, name: str) -> Any:
    return client.post(
        f"/api/v1/cases/{case_id}/evidence",
        headers=CSRF,
        files={"file": (name, content, "application/octet-stream")},
        data={"kind": kind},
    )


def _local_files(settings: Settings) -> list[Path]:
    root = Path(settings.storage_dir)
    return [p for sub in ("evidence", "business/certificates") for p in (root / sub).rglob("*")]


def test_evidence_round_trips_through_the_private_bucket_unchanged(
    client: TestClient, hosted_settings: Settings, fake_bucket: tuple[FakeBucket, str]
) -> None:
    bucket, _ = fake_bucket
    case_id = _case(client)
    uploaded = _upload(client, case_id, EVIDENCE_PDF, "invoice", "Invoice 201.pdf")
    assert uploaded.status_code == 201, uploaded.text
    evidence = uploaded.json()
    digest = hashlib.sha256(EVIDENCE_PDF).hexdigest()
    assert evidence["sha256"] == digest

    # Stored under the same content-addressed key as on disk, byte for byte.
    [(name, stored)] = bucket.objects.items()
    assert name.startswith("evidence/") and name.endswith(digest)
    assert stored == EVIDENCE_PDF
    assert _local_files(hosted_settings) == []  # nothing left on the server's disk
    assert all(auth == f"Bearer {SERVICE_KEY}" for _, _, auth in bucket.requests)

    download = client.get(f"/api/v1/evidence/{evidence['id']}/download")
    assert download.status_code == 200 and download.content == EVIDENCE_PDF
    assert download.headers["content-type"] == "application/pdf"
    # Same header FileResponse produced from disk: the space is percent-encoded.
    assert (
        download.headers["content-disposition"] == "attachment; filename*=utf-8''Invoice%20201.pdf"
    )
    assert download.headers["cache-control"] == "private, no-store"

    # Never overwritten: putting the same name again leaves the original object alone.
    blobs = SupabaseBlobs(fake_bucket[1], SERVICE_KEY, BUCKET)
    replacement = Path(hosted_settings.storage_dir) / "replacement"
    replacement.write_bytes(b"different bytes")
    blobs.put(name, replacement)
    assert bucket.objects[name] == EVIDENCE_PDF and len(bucket.objects) == 1
    assert not replacement.exists()  # the temp file is always cleaned up

    check = client.post(f"/api/v1/cases/{case_id}/integrity-check", headers=CSRF).json()
    assert check["result"] == "pass" and check["checked_files"] == 1


def test_evidence_pack_reads_the_original_bytes_and_tampering_is_detected(
    client: TestClient, fake_bucket: tuple[FakeBucket, str]
) -> None:
    bucket, _ = fake_bucket
    case_id = _case(client)
    assert _upload(client, case_id, EVIDENCE_PDF, "invoice", "invoice.pdf").status_code == 201
    assert _upload(client, case_id, EML, "email", "reply.eml").status_code == 201
    pack = client.get(f"/api/v1/cases/{case_id}/evidence-pack")
    assert pack.status_code == 200, pack.text
    archive = zipfile.ZipFile(io.BytesIO(pack.content))
    contents = {archive.read(n) for n in archive.namelist()}
    assert EVIDENCE_PDF in contents and EML in contents

    # Someone changes an object in the bucket: integrity fails and no pack is built.
    name = next(n for n, data in bucket.objects.items() if data == EML)
    bucket.objects[name] = EML + b" (edited)"
    check = client.post(f"/api/v1/cases/{case_id}/integrity-check", headers=CSRF).json()
    assert check["result"] == "fail"
    assert check["mismatches"][0]["detail"] == "hash does not match the recorded hash"
    refused = client.get(f"/api/v1/cases/{case_id}/evidence-pack")
    assert refused.status_code == 409 and refused.json()["code"] == "integrity_failed"

    # A missing object is reported, not served.
    del bucket.objects[name]
    evidence_id = next(
        e["id"]
        for e in client.get(f"/api/v1/cases/{case_id}/evidence").json()
        if e["original_filename"] == "reply.eml"
    )
    missing = client.get(f"/api/v1/evidence/{evidence_id}/download")
    assert missing.status_code == 409 and missing.json()["code"] == "integrity_failed"


def test_a_storage_outage_fails_safely_and_records_nothing(
    client: TestClient, fake_bucket: tuple[FakeBucket, str]
) -> None:
    bucket, _ = fake_bucket
    case_id = _case(client)
    bucket.fail = True
    response = _upload(client, case_id, EVIDENCE_PDF, "invoice", "invoice.pdf")
    assert response.status_code == 502 and response.json()["code"] == "storage_unavailable"
    assert SERVICE_KEY not in response.text and "127.0.0.1" not in response.text
    bucket.fail = False
    assert client.get(f"/api/v1/cases/{case_id}/evidence").json() == []  # no row without bytes


def test_certificates_and_reviewer_downloads_use_the_bucket(
    hosted_settings: Settings,
    frozen_clock: FrozenClock,
    fake_bucket: tuple[FakeBucket, str],
) -> None:
    bucket, _ = fake_bucket
    app = create_app(hosted_settings, clock=frozen_clock)
    supplier = TestClient(app)
    from tests.auth_helpers import signup

    assert signup(supplier, "hosted@example.com").status_code == 201
    assert (
        supplier.put("/api/v1/onboarding/draft", json=FULL_DRAFT, headers=CSRF).status_code == 200
    )
    certificate = pdf("hosted")
    upload = supplier.post(
        "/api/v1/onboarding/certificate",
        files={"file": ("udyam.pdf", certificate, "application/pdf")},
        headers=CSRF,
    )
    assert upload.status_code == 201
    names = [n for n in bucket.objects if n.startswith("business/certificates/")]
    assert len(names) == 1 and bucket.objects[names[0]] == certificate
    assert supplier.post("/api/v1/onboarding/submit", headers=CSRF).status_code == 200
    own = supplier.get(
        f"/api/v1/onboarding/certificates/{upload.json()['certificate']['id']}/download"
    )
    assert own.status_code == 200 and own.content == certificate

    db = Database(hosted_settings.database_url)
    try:
        with db.session() as session:
            reviewers.create_reviewer(
                session,
                frozen_clock,
                email="hosted-reviewer@example.com",
                full_name="Hosted Reviewer",
                password=TEST_PASSWORD,
                operator="pytest",
            )
    finally:
        db.dispose()
    reviewer = TestClient(app)
    assert login(reviewer, "hosted-reviewer@example.com").status_code == 200
    [item] = reviewer.get("/api/v1/review/submissions").json()["items"]
    detail = reviewer.get(f"/api/v1/review/submissions/{item['submission_id']}").json()
    assert detail["certificate"]["bytes_intact"] is True
    served = reviewer.get(f"/api/v1/review/submissions/{item['submission_id']}/certificate")
    assert served.status_code == 200 and served.content == certificate
    assert _local_files(hosted_settings) == []


def test_supabase_backend_needs_an_https_url_and_the_service_key(isolated_env: None) -> None:
    base = {**TEST_SETTINGS, "storage_backend": "supabase"}
    for extra in (
        {},
        {"supabase_url": "https://project.supabase.co"},
        {"supabase_service_role_key": SERVICE_KEY},
        {"supabase_url": "http://project.supabase.co", "supabase_service_role_key": SERVICE_KEY},
    ):
        with pytest.raises(Exception, match="STORAGE_BACKEND=supabase"):
            load_settings(_env_file=None, **{**base, **extra})
    ok = load_settings(
        _env_file=None,
        **base,
        supabase_url="https://project.supabase.co",
        supabase_service_role_key=SERVICE_KEY,
    )
    assert ok.storage_backend is StorageBackend.SUPABASE
    assert SERVICE_KEY not in repr(ok)  # secret never printed


def test_local_storage_stays_the_default(isolated_env: None) -> None:
    assert load_settings(_env_file=None, **TEST_SETTINGS).storage_backend is StorageBackend.LOCAL


def test_wrong_key_is_an_integration_failure(fake_bucket: tuple[FakeBucket, str]) -> None:
    _, url = fake_bucket
    blobs = SupabaseBlobs(url, "wrong-key", BUCKET)
    with pytest.raises(Exception, match="File storage is unavailable") as info:
        blobs.read("evidence/x/ab/" + "a" * 64)
    assert "wrong-key" not in str(info.value)
