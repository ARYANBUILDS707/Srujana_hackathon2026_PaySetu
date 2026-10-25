"""Evidence pack export: contents, manifest consistency, read-only behaviour and refusal."""

import hashlib
import io
import json
import re
import zipfile
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.clock import FrozenClock, format_utc_timestamp
from app.config import AppEnv, Settings
from app.db import Database
from app.documents.pack import UnsafeEntryNameError, cell, evidence_entry_name, safe_entry_name
from app.domain.integrity import ActorType, CheckResult, TimelineEvent, verify_chain
from app.domain.types import EvidenceKind
from app.main import create_app
from app.schemas.cases import EvidenceOut
from seed.demo import seed
from tests.auth_helpers import sign_in_as_demo

CSRF = {"Origin": "http://localhost:3000", "X-PaySetu-Client": "web"}
PDF = b"%PDF-1.4\n% SAMPLE invoice for the pack test, not real evidence\n"
EML = b"From: buyer@example.invalid\nSubject: Received\n\nGoods received (sample)."
PNG = b"\x89PNG\r\n\x1a\n SAMPLE challan photo bytes"

EXPECTED_DOCUMENTS = {
    "README_FIRST.md",
    "01_case_summary.md",
    "02_deemed_clock_and_interest.md",
    "03_timeline.md",
    "04_case_strength_checklist.md",
    "05_verification_report.md",
    "timeline.json",
    "manifest.json",
}


@pytest.fixture
def pack_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def client(pack_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    db = Database(pack_settings.database_url)
    try:
        with db.session() as session:
            seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    finally:
        db.dispose()
    with TestClient(create_app(pack_settings, clock=frozen_clock)) as test_client:
        sign_in_as_demo(test_client, pack_settings, frozen_clock)
        yield test_client


def _new_case(client: TestClient) -> str:
    buyer = client.get("/api/v1/buyers").json()[0]["id"]
    body = {
        "buyer_id": buyer,
        "invoice_number": "RF/26-27/118",
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


def _zip(response: Any) -> zipfile.ZipFile:
    assert response.status_code == 200, response.text
    return zipfile.ZipFile(io.BytesIO(response.content))


def _pack_url(case_id: str) -> str:
    return f"/api/v1/cases/{case_id}/evidence-pack"


@pytest.fixture
def full_case(client: TestClient) -> str:
    case_id = _new_case(client)
    assert _upload(client, case_id, PDF, "invoice", "invoice.pdf").status_code == 201
    assert _upload(client, case_id, PNG, "delivery_challan", "challan.png").status_code == 201
    assert _upload(client, case_id, EML, "email", "reply.eml").status_code == 201
    body = {
        "kind": "acknowledgement",
        "received_on": "2026-10-03",
        "channel": "email",
        "summary": "Accounts confirmed receipt (sample)",
    }
    assert (
        client.post(f"/api/v1/cases/{case_id}/responses", json=body, headers=CSRF).status_code
        == 201
    )
    assert client.post(f"/api/v1/cases/{case_id}/integrity-check", headers=CSRF).status_code == 200
    return case_id


# ------------------------------------------------------------------ contents and manifest


def test_export_returns_a_zip_with_the_expected_files(client: TestClient, full_case: str) -> None:
    response = client.get(_pack_url(full_case))
    archive = _zip(response)

    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == (
        'attachment; filename="PaySetu-evidence-pack-PS-2026-0001.zip"'
    )
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-length"] == str(len(response.content))
    assert archive.testzip() is None
    names = set(archive.namelist())
    evidence_names = {n for n in names if n.startswith("evidence/")}
    assert names - evidence_names == EXPECTED_DOCUMENTS
    assert len(evidence_names) == 3


def test_original_evidence_is_included_byte_for_byte(client: TestClient, full_case: str) -> None:
    archive = _zip(client.get(_pack_url(full_case)))
    included = {archive.read(n) for n in archive.namelist() if n.startswith("evidence/")}
    assert included == {PDF, PNG, EML}
    assert any(n.endswith(".pdf") for n in archive.namelist())
    assert any(n.endswith(".eml") for n in archive.namelist())


def test_manifest_matches_every_file_and_the_pack_id(client: TestClient, full_case: str) -> None:
    response = client.get(_pack_url(full_case))
    archive = _zip(response)
    manifest_bytes = archive.read("manifest.json")
    manifest = json.loads(manifest_bytes)

    assert response.headers["x-paysetu-pack-sha256"] == hashlib.sha256(manifest_bytes).hexdigest()
    listed = {f["path"]: f for f in manifest["files"]}
    assert set(listed) == set(archive.namelist()) - {"manifest.json"}  # nothing missing or extra
    for path, entry in listed.items():
        content = archive.read(path)
        assert entry["sha256"] == hashlib.sha256(content).hexdigest(), path
        assert entry["size_bytes"] == len(content), path
    for entry in manifest["files"]:
        if entry["role"] == "evidence":
            assert entry["sha256"] == entry["recorded_sha256"]
    assert manifest["demo"] is True and manifest["legally_certified"] is False
    assert manifest["case_reference"] == "PS-2026-0001"
    assert manifest["rule_set_version"] == "msmed-v1"
    assert "LR-21" in manifest["pending_reviews"]


def test_documents_carry_case_data_assumptions_and_labels(
    client: TestClient, full_case: str
) -> None:
    archive = _zip(client.get(_pack_url(full_case)))
    text = {n: archive.read(n).decode() for n in archive.namelist() if n.endswith(".md")}
    case = client.get(f"/api/v1/cases/{full_case}").json()
    interest = client.get(f"/api/v1/cases/{full_case}/interest").json()

    assert all("SYNTHETIC DEMO DATA. NOT LEGALLY CERTIFIED" in body for body in text.values())
    summary = text["01_case_summary.md"]
    for expected in (
        "DEMO",
        "Apex Auto Components",
        "RF/26-27/118",
        "500000.00",
        "2026-10-01",
        "M8 hex bolts (sample)",
        "Accounts confirmed receipt (sample)",
    ):
        assert expected in summary, expected

    clock = text["02_deemed_clock_and_interest.md"]
    assert case["clock"]["due_date"] in clock and "acknowledged the delivery" in clock
    assert "LR-21" in clock and "R4a" in clock and "pending_counsel" in clock
    assert f"Rs {interest['interest_accrued']}" in clock  # taken from the interest engine
    assert "NOT been verified against an RBI notification" in clock

    checklist = text["04_case_strength_checklist.md"]
    assert "does not score the case or predict any outcome" in checklist
    assert re.search(r"\| C06 \|.*\| met \|", checklist)  # the invoice was uploaded
    assert re.search(r"\| C08 \|.*\| met \|", checklist)  # the challan photo was uploaded

    readme = text["README_FIRST.md"]
    assert "No Section 63" in readme and "LR-16" in readme and "shasum -a 256" in readme
    assert not any("DRAFT certificate" in body for body in text.values())


def test_interest_unavailable_is_explained_not_invented(client: TestClient) -> None:
    buyer = client.get("/api/v1/buyers").json()[0]["id"]
    body = {
        "buyer_id": buyer,
        "invoice_number": "OLD-1",
        "invoice_date": "2026-09-01",
        "invoice_amount": "1000.00",
        "delivery_date": "2026-09-01",
        "deal_type": "verbal",
    }
    case_id = client.post("/api/v1/cases", json=body, headers=CSRF).json()["id"]
    archive = _zip(client.get(_pack_url(case_id)))
    clock = archive.read("02_deemed_clock_and_interest.md").decode()
    assert "Interest is **not calculated**" in clock and "rate_data_unavailable" in clock


def test_case_without_evidence_still_exports_with_gaps_listed(client: TestClient) -> None:
    case_id = _new_case(client)
    archive = _zip(client.get(_pack_url(case_id)))
    assert not any(n.startswith("evidence/") for n in archive.namelist())
    assert "No evidence files have been uploaded" in archive.read("01_case_summary.md").decode()
    assert re.search(
        r"\| C06 \|.*\| missing \|", archive.read("04_case_strength_checklist.md").decode()
    )


def test_timeline_json_lets_a_recipient_reverify_the_chain(
    client: TestClient, full_case: str
) -> None:
    archive = _zip(client.get(_pack_url(full_case)))
    document = json.loads(archive.read("timeline.json"))
    api_events = client.get(f"/api/v1/cases/{full_case}/timeline").json()
    assert [e["event_hash"] for e in document["events"]] == [e["event_hash"] for e in api_events]

    from datetime import date

    events = [
        TimelineEvent(
            case_id=document["case_id"],
            seq=e["seq"],
            event_type=e["event_type"],
            occurred_on=date.fromisoformat(e["occurred_on"]) if e["occurred_on"] else None,
            recorded_at=e["recorded_at"],
            actor_type=ActorType(e["actor_type"]),
            actor_id=e["actor_id"],
            payload=e["payload"],
            prev_hash=e["prev_hash"],
            event_hash=e["event_hash"],
        )
        for e in document["events"]
    ]
    assert verify_chain(events).result is CheckResult.PASS
    assert document["events"][-1]["event_type"] == "integrity_verified"


# ------------------------------------------------------------ read-only and determinism


def test_export_is_read_only_and_repeatable(client: TestClient, full_case: str) -> None:
    before = client.get(f"/api/v1/cases/{full_case}/timeline").json()
    first = client.get(_pack_url(full_case))
    second = client.get(_pack_url(full_case))
    after = client.get(f"/api/v1/cases/{full_case}/timeline").json()

    assert after == before  # no event was added or changed
    assert first.content == second.content  # same case + same clock = identical pack
    assert first.headers["x-paysetu-pack-sha256"] == second.headers["x-paysetu-pack-sha256"]
    evidence = client.get(f"/api/v1/cases/{full_case}/evidence").json()
    assert {e["sha256"] for e in evidence} == {
        hashlib.sha256(b).hexdigest() for b in (PDF, PNG, EML)
    }


# ------------------------------------------------------------------------ refusal paths


def _stored_files(settings: Settings) -> list[Path]:
    return [p for p in (Path(settings.storage_dir) / "evidence").rglob("*") if p.is_file()]


def test_tampered_evidence_blocks_the_export(
    client: TestClient, full_case: str, pack_settings: Settings
) -> None:
    before = client.get(f"/api/v1/cases/{full_case}/timeline").json()
    victim = next(p for p in _stored_files(pack_settings) if p.read_bytes() == PDF)
    victim.write_bytes(PDF + b" tampered")

    response = client.get(_pack_url(full_case))

    assert response.status_code == 409
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "integrity_failed" and "no pack was created" in body["detail"]
    assert body["request_id"] == response.headers["x-request-id"]
    evidence_id = next(
        e["id"]
        for e in client.get(f"/api/v1/cases/{full_case}/evidence").json()
        if e["sha256"] == hashlib.sha256(PDF).hexdigest()
    )
    assert {
        "field": f"file:{evidence_id}",
        "code": "integrity_mismatch",
        "message": "hash does not match the recorded hash",
    } in body["errors"]
    assert client.get(f"/api/v1/cases/{full_case}/timeline").json() == before  # nothing recorded


def test_missing_evidence_file_blocks_the_export(
    client: TestClient, full_case: str, pack_settings: Settings
) -> None:
    next(p for p in _stored_files(pack_settings) if p.read_bytes() == EML).unlink()
    response = client.get(_pack_url(full_case))
    assert response.status_code == 409 and response.json()["code"] == "integrity_failed"
    assert response.json()["errors"][0]["message"] == "missing"


def test_unknown_case_is_404_and_leaks_nothing(client: TestClient) -> None:
    response = client.get(_pack_url("00000000-0000-0000-0000-000000000000"))
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert client.get(_pack_url("does-not-exist")).status_code == 404
    assert client.get("/api/v1/cases/..%2f..%2fetc/evidence-pack").status_code == 404


def test_export_is_rate_limited_per_case(
    client: TestClient, full_case: str, frozen_clock: FrozenClock
) -> None:
    for _ in range(5):
        assert client.get(_pack_url(full_case)).status_code == 200
    limited = client.get(_pack_url(full_case))
    assert limited.status_code == 429 and limited.headers["retry-after"] == "3600"
    frozen_clock.advance(timedelta(hours=1))
    assert client.get(_pack_url(full_case)).status_code == 200


# ---------------------------------------------------------------------------- safety


@pytest.mark.parametrize(
    "filename",
    ["../../evil.pdf", "..\\..\\evil.pdf", "/etc/passwd.pdf", "a|b\nc`d.pdf", "x" * 400 + ".pdf"],
)
def test_hostile_filenames_cannot_create_unsafe_zip_entries(
    client: TestClient, filename: str
) -> None:
    case_id = _new_case(client)
    assert _upload(client, case_id, PDF, "invoice", filename).status_code == 201
    archive = _zip(client.get(_pack_url(case_id)))
    for name in archive.namelist():
        assert safe_entry_name(name) == name or name == "manifest.json"
        assert not name.startswith("/") and "\\" not in name and ".." not in name.split("/")
    assert len(set(archive.namelist())) == len(archive.namelist())
    summary = archive.read("01_case_summary.md").decode()
    # The filename is data inside a table cell, never structure: still one row per evidence file.
    assert sum(1 for line in summary.splitlines() if line.startswith("| evidence/01_")) == 1


def test_no_secrets_or_internal_paths_in_the_pack(
    client: TestClient, full_case: str, pack_settings: Settings
) -> None:
    archive = _zip(client.get(_pack_url(full_case)))
    supplier_id = client.get("/api/v1/supplier").json()["id"]
    forbidden = [
        str(pack_settings.storage_dir),
        supplier_id,
        "storage_key",
        pack_settings.token_hash_key.get_secret_value(),
        pack_settings.database_url,
    ]
    for name in archive.namelist():
        if name.startswith("evidence/"):
            continue  # raw evidence is the user's own bytes
        content = archive.read(name).decode()
        for needle in forbidden:
            assert needle not in content, (name, needle)


def test_pack_route_is_not_mounted_in_production(pack_settings: Settings) -> None:
    production = pack_settings.model_copy(
        update={
            "app_env": AppEnv.PRODUCTION,
            "public_base_url": "https://paysetu.example",
            "allow_nonlive_verified": True,
            "token_hash_key": SecretStr("production-test-key-0123456789abcdefghijkl"),
        }
    )
    with TestClient(create_app(production)) as client:
        assert client.get(_pack_url("anything")).status_code == 404
        assert client.get("/api/v1/health").status_code == 200


# ---------------------------------------------------------------- unit tests (builder)


@pytest.mark.parametrize(
    "name",
    [
        "../x",
        "/abs",
        "a//b",
        "a\\b",
        "",
        ".hidden",
        "a/../b",
        "x" * 130,
        "has space.txt",
        "evil\n.txt",
        "a/./b",
        "C:evil",
    ],
)
def test_unsafe_entry_names_are_rejected(name: str) -> None:
    with pytest.raises(UnsafeEntryNameError):
        safe_entry_name(name)


@pytest.mark.parametrize(
    "name", ["README_FIRST.md", "evidence/01_invoice_ab12cd34.pdf", "a/b/c.txt"]
)
def test_safe_entry_names_are_accepted(name: str) -> None:
    assert safe_entry_name(name) == name


def test_evidence_names_come_from_our_fields_only() -> None:
    item = EvidenceOut(
        id="e1",
        kind=EvidenceKind.INVOICE,
        original_filename="../../x.pdf",
        mime_type="application/pdf",
        size_bytes=3,
        sha256="ab" * 32,
        received_at="2026-11-01T00:00:00.000Z",
        note=None,
        excluded=False,
    )
    assert evidence_entry_name(1, item) == "evidence/01_invoice_abababab.pdf"
    unknown = item.model_copy(update={"mime_type": "application/x-weird"})
    assert evidence_entry_name(12, unknown).endswith(".bin")


def test_table_cells_neutralise_markdown_structure() -> None:
    assert cell("a | b\nc `d` \\ e") == "a \\| b c 'd' \\\\ e"
    assert cell(None) == "-" and cell("   ") == "-"
