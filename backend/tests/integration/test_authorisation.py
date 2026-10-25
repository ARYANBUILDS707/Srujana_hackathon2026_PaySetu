"""Phase 6: every supplier route needs a session, and suppliers never see each other's data.

Two suppliers share one app: the seeded demo supplier (user A, signed in through the demo
account) and a freshly signed-up supplier (user B). Every request B makes for A's records must
answer 404, exactly like a missing record, and must leave A's case untouched.
"""

import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.clock import FrozenClock, format_utc_timestamp
from app.config import Settings
from app.db import Database
from app.main import create_app
from seed.demo import seed
from tests.auth_helpers import CSRF, sign_in_as_demo, signup

PDF = b"%PDF-1.4\n% SAMPLE authorisation test document, not real evidence\n"
PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    # Phase 6.1: token-authenticated (reset) or answer identically for any email (forgot).
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/reset-password"),
}


@pytest.fixture
def app_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def app(app_settings: Settings, frozen_clock: FrozenClock) -> Any:
    db = Database(app_settings.database_url)
    try:
        with db.session() as session:
            seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    finally:
        db.dispose()
    return create_app(app_settings, clock=frozen_clock)


@pytest.fixture
def owner(app: Any, app_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    with TestClient(app) as client:
        sign_in_as_demo(client, app_settings, frozen_clock)
        yield client


@pytest.fixture
def intruder(app: Any) -> TestClient:
    """A second supplier, signed in: ownership (404) is what stops it."""
    client = TestClient(app)
    assert signup(client, "intruder@example.com").status_code == 201
    return client


@pytest.fixture
def owned(owner: TestClient) -> dict[str, str]:
    """A's case with a buyer, an evidence file and an open objection."""
    buyer_id = owner.get("/api/v1/buyers").json()[0]["id"]
    case = owner.post(
        "/api/v1/cases",
        json={
            "buyer_id": buyer_id,
            "invoice_number": "RF/26-27/118",
            "invoice_date": "2026-10-01",
            "invoice_amount": "500000.00",
            "delivery_date": "2026-10-01",
            "deal_type": "verbal",
        },
        headers=CSRF,
    ).json()
    evidence = owner.post(
        f"/api/v1/cases/{case['id']}/evidence",
        headers=CSRF,
        files={"file": ("invoice.pdf", PDF, "application/pdf")},
        data={"kind": "invoice"},
    ).json()
    responses = owner.post(
        f"/api/v1/cases/{case['id']}/responses",
        json={
            "kind": "objection",
            "received_on": "2026-10-05",
            "channel": "email",
            "summary": "Sample objection (TEST)",
        },
        headers=CSRF,
    ).json()
    return {
        "case_id": case["id"],
        "buyer_id": buyer_id,
        "evidence_id": evidence["id"],
        "response_id": responses[0]["id"],
    }


def _supplier_routes(app: Any) -> list[tuple[str, str]]:
    """Every documented API operation except the public ones (taken from the OpenAPI schema)."""
    return [
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if (method.upper(), path) not in PUBLIC_ROUTES
    ]


# ------------------------------------------------------------------ unauthenticated


def test_every_supplier_route_requires_a_session(app: Any) -> None:
    routes = _supplier_routes(app)
    assert len(routes) >= 17  # all case, buyer, evidence, timeline, interest and pack routes
    with TestClient(app) as anonymous:
        for method, path in routes:
            url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)
            response = anonymous.request(method, url, headers=CSRF, json={})
            assert response.status_code == 401, (method, path, response.status_code)
            assert response.json()["code"] == "unauthenticated"


def test_unauthenticated_requests_reveal_nothing_about_real_ids(
    app: Any, owned: dict[str, str]
) -> None:
    anonymous = TestClient(app)
    for path in (
        f"/api/v1/cases/{owned['case_id']}",
        f"/api/v1/evidence/{owned['evidence_id']}/download",
        f"/api/v1/cases/{owned['case_id']}/evidence-pack",
    ):
        response = anonymous.get(path)
        assert response.status_code == 401 and owned["case_id"] not in response.text


# ------------------------------------------------------------------- cross-supplier


def test_another_supplier_sees_none_of_my_records(
    owner: TestClient, intruder: TestClient, owned: dict[str, str]
) -> None:
    assert intruder.get("/api/v1/cases").json() == []
    assert owned["buyer_id"] not in {b["id"] for b in intruder.get("/api/v1/buyers").json()}
    assert "DEMO" not in intruder.get("/api/v1/supplier").json()["legal_name"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/cases/{case_id}"),
        ("GET", "/api/v1/cases/{case_id}/checklist"),
        ("GET", "/api/v1/cases/{case_id}/interest"),
        ("GET", "/api/v1/cases/{case_id}/responses"),
        ("GET", "/api/v1/cases/{case_id}/evidence"),
        ("GET", "/api/v1/cases/{case_id}/timeline"),
        ("GET", "/api/v1/cases/{case_id}/evidence-pack"),
        ("GET", "/api/v1/evidence/{evidence_id}/download"),
        ("POST", "/api/v1/cases/{case_id}/integrity-check"),
    ],
)
def test_reading_another_suppliers_records_is_404(
    owner: TestClient, intruder: TestClient, owned: dict[str, str], method: str, path: str
) -> None:
    response = intruder.request(method, path.format(**owned), headers=CSRF)
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert owned["case_id"] not in response.text
    assert "invoice.pdf" not in response.text and "PDF" not in response.text
    # The owner still can.
    assert owner.request(method, path.format(**owned), headers=CSRF).status_code == 200


def test_writing_to_another_suppliers_case_is_404_and_changes_nothing(
    owner: TestClient, intruder: TestClient, owned: dict[str, str]
) -> None:
    case_id = owned["case_id"]
    before = owner.get(f"/api/v1/cases/{case_id}/timeline").json()

    response = intruder.post(
        f"/api/v1/cases/{case_id}/responses",
        json={
            "kind": "acknowledgement",
            "received_on": "2026-10-06",
            "channel": "email",
            "summary": "Injected (TEST)",
        },
        headers=CSRF,
    )
    assert response.status_code == 404
    removal = intruder.post(
        f"/api/v1/cases/{case_id}/responses/{owned['response_id']}/remove-objection",
        json={"removed_on": "2026-10-07"},
        headers=CSRF,
    )
    assert removal.status_code == 404
    upload = intruder.post(
        f"/api/v1/cases/{case_id}/evidence",
        headers=CSRF,
        files={"file": ("x.pdf", b"%PDF-1.4 injected", "application/pdf")},
        data={"kind": "other"},
    )
    assert upload.status_code == 404
    # Using A's buyer for B's own case is refused too: buyer IDs are scoped like cases.
    stolen_buyer = intruder.post(
        "/api/v1/cases",
        json={
            "buyer_id": owned["buyer_id"],
            "invoice_number": "X-1",
            "invoice_date": "2026-10-01",
            "invoice_amount": "100.00",
            "delivery_date": "2026-10-01",
            "deal_type": "verbal",
        },
        headers=CSRF,
    )
    assert stolen_buyer.status_code == 404

    assert owner.get(f"/api/v1/cases/{case_id}/timeline").json() == before
    assert len(owner.get(f"/api/v1/cases/{case_id}/evidence").json()) == 1
    responses = owner.get(f"/api/v1/cases/{case_id}/responses").json()
    assert len(responses) == 1 and responses[0]["objection_removed_on"] is None


def test_owner_fields_in_request_bodies_are_rejected(
    intruder: TestClient, owned: dict[str, str]
) -> None:
    response = intruder.post(
        "/api/v1/cases",
        json={
            "buyer_id": owned["buyer_id"],
            "supplier_id": "anything",
            "invoice_number": "X-1",
            "invoice_date": "2026-10-01",
            "invoice_amount": "100.00",
            "delivery_date": "2026-10-01",
            "deal_type": "verbal",
        },
        headers=CSRF,
    )
    assert response.status_code == 422  # extra fields are forbidden, never trusted


def test_each_supplier_gets_its_own_case_numbering_and_pack(
    owner: TestClient, intruder: TestClient, owned: dict[str, str]
) -> None:
    buyer = intruder.post(
        "/api/v1/buyers", json={"legal_name": "Sample Buyer B (TEST)"}, headers=CSRF
    ).json()
    created = intruder.post(
        "/api/v1/cases",
        json={
            "buyer_id": buyer["id"],
            "invoice_number": "B-1",
            "invoice_date": "2026-10-01",
            "invoice_amount": "1000.00",
            "delivery_date": "2026-10-01",
            "deal_type": "verbal",
        },
        headers=CSRF,
    )
    assert created.status_code == 201 and created.json()["reference"] == "PS-2026-0001"
    own_pack = intruder.get(f"/api/v1/cases/{created.json()['id']}/evidence-pack")
    assert own_pack.status_code == 200 and own_pack.headers["content-type"] == "application/zip"
    assert [c["id"] for c in owner.get("/api/v1/cases").json()] == [owned["case_id"]]


def test_logging_out_stops_access_immediately(owner: TestClient, owned: dict[str, str]) -> None:
    assert owner.get(f"/api/v1/cases/{owned['case_id']}").status_code == 200
    assert owner.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    assert owner.get(f"/api/v1/cases/{owned['case_id']}").status_code == 401
    assert owner.get(f"/api/v1/evidence/{owned['evidence_id']}/download").status_code == 401
