"""Demo vertical slice: cases, DeemedClock, responses, evidence, integrity, checklist, interest."""

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.clock import FrozenClock, format_utc_timestamp
from app.config import Settings, load_settings
from app.db import Database
from app.main import create_app
from seed.demo import seed
from tests.conftest import TEST_SETTINGS

CSRF = {"Origin": "http://localhost:3000", "X-PaySetu-Client": "web"}
PDF = b"%PDF-1.4\n% SAMPLE test document, not real evidence\n"
# Frozen "today" is 1 Nov 2026 (conftest FROZEN_INSTANT).


@pytest.fixture
def demo_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url, "max_upload_mb": 1})


def _seed(settings: Settings, clock: FrozenClock) -> None:
    db = Database(settings.database_url)
    try:
        with db.session() as session:
            seed(session, format_utc_timestamp(clock.now_utc()))
    finally:
        db.dispose()


@pytest.fixture
def client(demo_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    _seed(demo_settings, frozen_clock)
    with TestClient(create_app(demo_settings, clock=frozen_clock)) as test_client:
        yield test_client


@pytest.fixture
def buyer_id(client: TestClient) -> str:
    buyers = client.get("/api/v1/buyers").json()
    assert len(buyers) == 1 and "SAMPLE" in buyers[0]["legal_name"]
    return str(buyers[0]["id"])


def _case(client: TestClient, default_buyer_id: str, **changes: Any) -> Any:
    body = {
        "buyer_id": default_buyer_id,
        "invoice_number": "RF/26-27/118",
        "invoice_date": "2026-10-01",
        "invoice_amount": "500000.00",
        "delivery_date": "2026-10-01",
        "deal_type": "verbal",
        **changes,
    }
    return client.post("/api/v1/cases", json=body, headers=CSRF)


def _upload(
    client: TestClient,
    case_id: str,
    content: bytes = PDF,
    kind: str = "invoice",
    name: str = "inv.pdf",
) -> Any:
    return client.post(
        f"/api/v1/cases/{case_id}/evidence",
        headers=CSRF,
        files={"file": (name, content, "application/octet-stream")},
        data={"kind": kind},
    )


# ------------------------------------------------------------------ supplier, buyers


def test_endpoints_need_the_seeded_demo_supplier(
    demo_settings: Settings, frozen_clock: FrozenClock
) -> None:
    with TestClient(create_app(demo_settings, clock=frozen_clock)) as client:
        response = client.get("/api/v1/supplier")
    assert response.status_code == 409 and response.json()["code"] == "profile_incomplete"


def test_supplier_is_synthetic_and_eligibility_is_reported(client: TestClient) -> None:
    body = client.get("/api/v1/supplier").json()
    assert "DEMO" in body["legal_name"] and body["demo_mode"] is True
    assert body["eligibility_verdict"] == "eligible_with_warnings"  # self-declared Udyam
    assert any(
        r["code"] == "udyam_evidence" and r["status"] == "warning"
        for r in body["eligibility_reasons"]
    )


def test_create_buyer_validates_gstin(client: TestClient) -> None:
    created = client.post("/api/v1/buyers", json={"legal_name": "Test Buyer"}, headers=CSRF)
    assert created.status_code == 201 and created.json()["legal_name"] == "Test Buyer"
    bad = client.post("/api/v1/buyers", json={"legal_name": "X", "gstin": "123"}, headers=CSRF)
    assert bad.status_code == 422 and bad.json()["code"] == "validation_failed"


def test_seed_is_idempotent(demo_settings: Settings, frozen_clock: FrozenClock) -> None:
    db = Database(demo_settings.database_url)
    try:
        with db.session() as session:
            first = seed(session, format_utc_timestamp(frozen_clock.now_utc()))
        with db.session() as session:
            second = seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    finally:
        db.dispose()
    assert len(first) == 3 and second == []


# ------------------------------------------------------------------ cases + DeemedClock


def test_create_and_retrieve_case_with_deemed_acceptance(client: TestClient, buyer_id: str) -> None:
    created = _case(client, buyer_id)
    assert created.status_code == 201
    case = created.json()
    assert case["reference"] == "PS-2026-0001" and case["invoice_amount"] == "500000.00"
    clock = case["clock"]
    assert clock["acceptance_state"] == "accepted" and clock["acceptance_basis"] == "deemed"
    assert (clock["window_end"], clock["due_date"], clock["interest_start"]) == (
        "2026-10-16",
        "2026-10-16",
        "2026-10-17",
    )
    assert clock["payment_state"] == "overdue" and clock["days_overdue"] == 16
    assert "LR-21" in clock["pending_reviews"] and clock["unconfirmed_rules"]
    assert case["demo_mode"] is True and case["recorded_late_days"] == 31

    fetched = client.get(f"/api/v1/cases/{case['id']}").json()
    assert fetched["clock"] == clock
    listed = client.get("/api/v1/cases").json()
    assert [c["id"] for c in listed] == [case["id"]] and listed[0]["payment_state"] == "overdue"
    assert _case(client, buyer_id).json()["reference"] == "PS-2026-0002"


def test_interest_uses_the_engine_and_labels_the_unverified_rate(
    client: TestClient, buyer_id: str
) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    interest = client.get(f"/api/v1/cases/{case_id}/interest").json()
    assert interest["status"] == "computed" and interest["uses_unverified_rates"] is True
    # 17 Oct to 1 Nov inclusive = 16 days: 500000 × 17.25% × 16 / 365 = 3780.82 (hand-computed).
    assert interest["interest_accrued"] == "3780.82"
    assert interest["periods"][0]["annual_rate_percent"] == "17.25"
    assert interest["periods"][0]["rate_verified"] is False
    assert "NOT verified" in interest["message"]
    amounts = client.get(f"/api/v1/cases/{case_id}").json()["amounts"]
    assert amounts["interest"] == "3780.82" and amounts["total_claimable"] == "503780.82"


def test_interest_is_not_invented_without_rate_data(client: TestClient, buyer_id: str) -> None:
    # Interest would start 17 Sep 2026, before the only recorded rate (7 Oct 2026).
    case_id = _case(client, buyer_id, delivery_date="2026-09-01", invoice_date="2026-09-01").json()[
        "id"
    ]
    interest = client.get(f"/api/v1/cases/{case_id}/interest").json()
    assert interest["status"] == "rate_data_unavailable" and interest["interest_accrued"] is None
    assert client.get(f"/api/v1/cases/{case_id}").json()["amounts"]["interest"] is None


def test_window_open_case_shows_countdown_and_next_action(
    client: TestClient, buyer_id: str
) -> None:
    case = _case(client, buyer_id, delivery_date="2026-10-25", invoice_date="2026-10-25").json()
    assert case["clock"]["acceptance_state"] == "window_open"
    assert case["clock"]["window_day"] == 7 and case["clock"]["window_days_remaining"] == 8
    assert case["next_action"]["code"] == "send_intimation"
    assert case["amounts"]["interest_status"] == "not_applicable"


@pytest.mark.parametrize(
    ("changes", "status", "code"),
    [
        ({"delivery_date": "2026-11-02"}, 422, "validation_failed"),  # future (domain rule)
        ({"agreed_payment_days": 30}, 422, "validation_failed"),  # verbal with terms
        ({"invoice_amount": "100.001"}, 422, "validation_failed"),
        ({"invoice_amount": "0"}, 422, "validation_failed"),
        ({"surprise": 1}, 422, "validation_failed"),
        ({"buyer_id": "00000000-0000-0000-0000-000000000000"}, 404, "not_found"),
    ],
)
def test_case_validation(
    client: TestClient, buyer_id: str, changes: dict[str, Any], status: int, code: str
) -> None:
    response = _case(client, buyer_id, **changes)
    assert response.status_code == status and response.json()["code"] == code


def test_written_terms_over_45_days_are_capped(client: TestClient, buyer_id: str) -> None:
    clock = _case(client, buyer_id, deal_type="written", agreed_payment_days=60).json()["clock"]
    assert clock["terms_capped_at_45"] is True and clock["due_date"] == "2026-11-15"


def test_unknown_case_is_404_and_writes_need_csrf(client: TestClient, buyer_id: str) -> None:
    assert client.get("/api/v1/cases/does-not-exist").json()["code"] == "not_found"
    body = {
        "buyer_id": buyer_id,
        "invoice_number": "X",
        "invoice_date": "2026-10-01",
        "invoice_amount": "1.00",
        "delivery_date": "2026-10-01",
        "deal_type": "verbal",
    }
    response = client.post("/api/v1/cases", json=body)
    assert response.status_code == 403 and response.json()["code"] == "csrf_rejected"
    assert client.get("/api/v1/cases").json() == []


# ------------------------------------------------------------------- buyer responses


def test_objection_then_removal_moves_acceptance(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id, delivery_date="2026-10-20", invoice_date="2026-10-20").json()[
        "id"
    ]
    url = f"/api/v1/cases/{case_id}/responses"
    objection = {
        "kind": "objection",
        "received_on": "2026-10-22",
        "channel": "email",
        "summary": "Thread defects in 2,000 pcs (sample)",
    }
    responses = client.post(url, json=objection, headers=CSRF)
    assert responses.status_code == 201 and responses.json()[0]["affects_acceptance"] is True
    assert (
        client.get(f"/api/v1/cases/{case_id}").json()["clock"]["acceptance_state"]
        == "objection_raised"
    )

    response_id = responses.json()[0]["id"]
    removal = client.post(
        f"{url}/{response_id}/remove-objection", json={"removed_on": "2026-10-28"}, headers=CSRF
    )
    assert removal.status_code == 200 and removal.json()[0]["objection_removed_on"] == "2026-10-28"
    clock = client.get(f"/api/v1/cases/{case_id}").json()["clock"]
    assert (
        clock["acceptance_basis"] == "objection_removed"
        and clock["acceptance_date"] == "2026-10-28"
    )

    again = client.post(
        f"{url}/{response_id}/remove-objection", json={"removed_on": "2026-10-29"}, headers=CSRF
    )
    assert again.status_code == 409 and again.json()["code"] == "invalid_state"


def test_late_and_phone_objections_do_not_move_acceptance(
    client: TestClient, buyer_id: str
) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    url = f"/api/v1/cases/{case_id}/responses"
    late = {"kind": "objection", "received_on": "2026-10-20", "channel": "email", "summary": "late"}
    phone = {
        "kind": "objection",
        "received_on": "2026-10-03",
        "channel": "phone_note",
        "summary": "call",
    }
    client.post(url, json=late, headers=CSRF)
    listed = client.post(url, json=phone, headers=CSRF).json()
    assert all(not r["affects_acceptance"] for r in listed)
    assert client.get(f"/api/v1/cases/{case_id}").json()["clock"]["acceptance_basis"] == "deemed"


def test_response_dates_are_validated(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    body = {"kind": "objection", "received_on": "2026-09-01", "channel": "email", "summary": "x"}
    response = client.post(f"/api/v1/cases/{case_id}/responses", json=body, headers=CSRF)
    assert response.status_code == 422 and response.json()["code"] == "validation_failed"


# ------------------------------------------------------------- evidence and integrity


def test_evidence_upload_hash_download_and_checklist(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    before = client.get(f"/api/v1/cases/{case_id}/checklist").json()
    assert {i["item_id"]: i["status"] for i in before["items"]}["C06"] == "missing"

    uploaded = _upload(client, case_id)
    assert uploaded.status_code == 201
    item = uploaded.json()
    assert item["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert item["mime_type"] == "application/pdf" and item["size_bytes"] == len(PDF)

    assert [e["id"] for e in client.get(f"/api/v1/cases/{case_id}/evidence").json()] == [item["id"]]
    download = client.get(f"/api/v1/evidence/{item['id']}/download")
    assert download.content == PDF
    assert download.headers["content-disposition"].startswith("attachment")
    assert download.headers["cache-control"] == "private, no-store"

    after = client.get(f"/api/v1/cases/{case_id}/checklist").json()
    statuses = {i["item_id"]: i["status"] for i in after["items"]}
    assert statuses["C06"] == "met" and statuses["C08"] == "missing"
    assert after["required_met"] == before["required_met"] + 1
    assert (
        client.get(f"/api/v1/cases/{case_id}").json()["next_action"]["code"] == "complete_evidence"
    )


@pytest.mark.parametrize(
    ("content", "name", "status", "code"),
    [
        (b"\x00\x01\x02 binary", "x.bin", 415, "unsupported_file_type"),
        (b"", "empty.pdf", 415, "unsupported_file_type"),
        (b"%PDF-" + b"x" * (1024 * 1024), "big.pdf", 413, "file_too_large"),
    ],
)
def test_upload_rejections(
    client: TestClient, buyer_id: str, content: bytes, name: str, status: int, code: str
) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    response = _upload(client, case_id, content=content, name=name)
    assert response.status_code == status and response.json()["code"] == code
    assert client.get(f"/api/v1/cases/{case_id}/evidence").json() == []


def test_duplicate_upload_and_text_types(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    _upload(client, case_id)
    duplicate = _upload(client, case_id)
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "duplicate_evidence"
    eml = _upload(
        client, case_id, b"From: buyer@example.invalid\nSubject: ok\n\nReceived.", "email", "m.eml"
    )
    chat = _upload(client, case_id, "WhatsApp export ✓ sample".encode(), "chat_export", "chat.txt")
    assert eml.json()["mime_type"] == "message/rfc822" and chat.json()["mime_type"] == "text/plain"


def test_integrity_check_passes_then_detects_tampering(
    client: TestClient, buyer_id: str, demo_settings: Settings
) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    item = _upload(client, case_id).json()
    url = f"/api/v1/cases/{case_id}/integrity-check"

    first = client.post(url, headers=CSRF).json()
    assert (
        first["result"] == "pass" and first["checked_files"] == 1 and first["checked_events"] == 2
    )
    statuses = {
        i["item_id"]: i["status"]
        for i in client.get(f"/api/v1/cases/{case_id}/checklist").json()["items"]
    }
    assert statuses["C16"] == "met"

    stored = Path(demo_settings.storage_dir) / "evidence"
    target = next(p for p in stored.rglob("*") if p.is_file())
    target.write_bytes(PDF + b"tampered")  # flip the stored bytes

    second = client.post(url, headers=CSRF).json()
    assert second["result"] == "fail"
    assert second["mismatches"][0] == {
        "type": "file",
        "reference": item["id"],
        "detail": "hash does not match the recorded hash",
    }
    assert (
        client.get(f"/api/v1/cases/{case_id}").json()["next_action"]["code"] == "review_integrity"
    )

    events = client.get(f"/api/v1/cases/{case_id}/timeline").json()
    assert [e["event_type"] for e in events] == [
        "case_created",
        "evidence_added",
        "integrity_verified",
        "integrity_failed",
    ]
    assert all(b["prev_hash"] == a["event_hash"] for a, b in zip(events, events[1:], strict=False))


def test_timeline_and_evidence_rows_are_append_only(
    client: TestClient, buyer_id: str, demo_settings: Settings
) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    _upload(client, case_id)
    db = Database(demo_settings.database_url)
    try:
        for statement in (
            "UPDATE timeline_events SET payload = '{}'",
            "DELETE FROM timeline_events",
            "DELETE FROM evidence_items",
            "UPDATE evidence_items SET sha256 = '" + "0" * 64 + "'",
        ):
            with (
                pytest.raises(DatabaseError, match="append-only"),
                db.session() as session,
                session.begin(),
            ):
                session.execute(text(statement))
    finally:
        db.dispose()


# ------------------------------------------------------------------ demo-mode guard


def test_demo_routes_are_not_mounted_in_production(isolated_env: None, tmp_path: Path) -> None:
    production = load_settings(
        _env_file=None,
        **{
            **TEST_SETTINGS,
            "app_env": "production",
            "public_base_url": "https://paysetu.example",
            "database_url": f"sqlite:///{tmp_path / 'prod.db'}",
            "storage_dir": str(tmp_path),
            "token_hash_key": "production-test-key-0123456789abcdefghijkl",
            "allow_nonlive_verified": True,
        },
    )
    with TestClient(create_app(production)) as client:
        assert client.get("/api/v1/cases").status_code == 404
        assert client.get("/api/v1/supplier").status_code == 404
        assert client.get("/api/v1/health").status_code == 200


# ------------------------------------------------------------- remaining error paths


def test_response_listing_and_lookup_errors(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id, delivery_date="2026-10-25", invoice_date="2026-10-25").json()[
        "id"
    ]
    url = f"/api/v1/cases/{case_id}/responses"
    ack = {
        "kind": "acknowledgement",
        "received_on": "2026-10-26",
        "channel": "email",
        "summary": "ok",
    }
    client.post(url, json=ack, headers=CSRF)
    listed = client.get(url).json()
    assert len(listed) == 1 and listed[0]["note"].startswith("Acknowledgement within the window")

    missing = client.post(
        f"{url}/nope/remove-objection", json={"removed_on": "2026-10-28"}, headers=CSRF
    )
    assert missing.status_code == 404
    not_objection = client.post(
        f"{url}/{listed[0]['id']}/remove-objection", json={"removed_on": "2026-10-28"}, headers=CSRF
    )
    assert not_objection.status_code == 409 and not_objection.json()["code"] == "invalid_state"
    foreign = {**ack, "evidence_item_id": "not-in-this-case"}
    assert client.post(url, json=foreign, headers=CSRF).status_code == 404


def test_evidence_linked_response_and_download_404(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    item = _upload(
        client, case_id, b"From: a@example.invalid\n\nobjection", "email", "o.eml"
    ).json()
    body = {
        "kind": "objection",
        "received_on": "2026-10-03",
        "channel": "email",
        "summary": "x",
        "evidence_item_id": item["id"],
    }
    linked = client.post(f"/api/v1/cases/{case_id}/responses", json=body, headers=CSRF)
    assert linked.status_code == 201 and linked.json()[0]["evidence_item_id"] == item["id"]
    assert client.get("/api/v1/evidence/unknown/download").status_code == 404


def test_case_storage_cap(demo_settings: Settings, frozen_clock: FrozenClock) -> None:
    capped = demo_settings.model_copy(update={"max_upload_mb": 1, "max_case_storage_mb": 1})
    _seed(capped, frozen_clock)
    with TestClient(create_app(capped, clock=frozen_clock)) as client:
        buyer = client.get("/api/v1/buyers").json()[0]["id"]
        case_id = _case(client, buyer).json()["id"]
        assert _upload(client, case_id, b"%PDF-" + b"a" * 700_000).status_code == 201
        full = _upload(client, case_id, b"%PDF-" + b"b" * 700_000, name="b.pdf")
    assert full.status_code == 413 and full.json()["code"] == "case_storage_full"


def test_interest_before_start_and_explicit_as_of(client: TestClient, buyer_id: str) -> None:
    case_id = _case(client, buyer_id).json()["id"]
    early = client.get(f"/api/v1/cases/{case_id}/interest", params={"as_of": "2026-10-16"}).json()
    assert early["status"] == "not_yet_due" and early["periods"] == []
