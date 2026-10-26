"""Phase 7C: reviewer role, review queue, manual checks, decisions and their boundaries."""

import io
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DatabaseError

from app.clock import FrozenClock
from app.config import Settings
from app.db import Database
from app.errors import Conflict
from app.main import create_app
from app.models import BusinessReview, BusinessSubmission, ReviewerGrant, UdyamClaim
from app.schemas.review import DecisionIn
from app.services import review as review_service
from app.services import reviewers
from app.services.auth import ReviewerPrincipal
from app.storage.business_store import BusinessDocumentStore
from tests.auth_helpers import CSRF, TEST_PASSWORD, login, signup
from tests.integration.test_onboarding import FULL_DRAFT, UDYAM, pdf
from tools import reviewer as reviewer_cli

REVIEWER_EMAIL = "reviewer@example.com"
API = "/api/v1/review"
PORTAL_CHECK: dict[str, Any] = {
    "source": "udyam_portal",
    "source_detail": "Udyam Registration portal, Print / Verify page, looked up manually",
    "checked_on": "2026-11-01",
    "items": [
        {"field": "udyam_number", "observed_value": UDYAM, "result": "match"},
        {
            "field": "enterprise_name",
            "observed_value": "Sample Fasteners (TEST)",
            "result": "match",
        },
    ],
}
INFO_REASON = "Please upload the full certificate including page 2."
NOW = "2026-11-01T10:30:00.000Z"  # FROZEN_INSTANT as stored
INTERNAL_NOTE = "INTERNAL-ONLY-NOTE: portal showed a different PIN."


@pytest.fixture
def rv_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def db(rv_settings: Settings) -> Iterator[Database]:
    database = Database(rv_settings.database_url)
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture
def app(rv_settings: Settings, frozen_clock: FrozenClock) -> Any:
    return create_app(rv_settings, clock=frozen_clock)


def _supplier(app: Any, email: str) -> TestClient:
    client = TestClient(app)
    assert signup(client, email).status_code == 201
    return client


def _submitted(app: Any, email: str, label: str, **changes: Any) -> TestClient:
    client = _supplier(app, email)
    draft = {**FULL_DRAFT, **changes}
    assert client.put("/api/v1/onboarding/draft", json=draft, headers=CSRF).status_code == 200
    upload = client.post(
        "/api/v1/onboarding/certificate",
        files={"file": ("udyam.pdf", pdf(label), "application/pdf")},
        headers=CSRF,
    )
    assert upload.status_code == 201
    assert client.post("/api/v1/onboarding/submit", headers=CSRF).status_code == 200
    return client


def _make_reviewer(db: Database, clock: FrozenClock, email: str = REVIEWER_EMAIL) -> None:
    with db.session() as session:
        reviewers.create_reviewer(
            session,
            clock,
            email=email,
            full_name="Sample Reviewer",
            password=TEST_PASSWORD,
            operator="pytest",
        )


@pytest.fixture
def reviewer(app: Any, db: Database, frozen_clock: FrozenClock) -> TestClient:
    _make_reviewer(db, frozen_clock)
    client = TestClient(app)
    assert login(client, REVIEWER_EMAIL).status_code == 200
    return client


@pytest.fixture
def supplier(app: Any) -> TestClient:
    return _submitted(app, "owner@example.com", "owner")


def _pending(reviewer: TestClient) -> list[dict[str, Any]]:
    response = reviewer.get(f"{API}/submissions")
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def _only_pending_id(reviewer: TestClient) -> str:
    items = _pending(reviewer)
    assert len(items) == 1
    return str(items[0]["submission_id"])


def _check(client: TestClient, submission_id: str, **changes: Any) -> Any:
    return client.post(
        f"{API}/submissions/{submission_id}/checks", json={**PORTAL_CHECK, **changes}, headers=CSRF
    )


def _decide(client: TestClient, submission_id: str, decision: str, **extra: Any) -> Any:
    body = {
        "decision": decision,
        "reason": extra.pop("reason", "Decision reason for test."),
        **extra,
    }
    return client.post(f"{API}/submissions/{submission_id}/decision", json=body, headers=CSRF)


def _onboarding(client: TestClient) -> dict[str, Any]:
    data: dict[str, Any] = client.get("/api/v1/onboarding").json()
    return data


def _all_review_requests(submission_id: str) -> list[tuple[str, str, dict[str, Any] | None]]:
    return [
        ("GET", f"{API}/submissions", None),
        ("GET", f"{API}/submissions/{submission_id}", None),
        ("GET", f"{API}/submissions/{submission_id}/certificate", None),
        ("POST", f"{API}/submissions/{submission_id}/checks", PORTAL_CHECK),
        (
            "POST",
            f"{API}/submissions/{submission_id}/decision",
            {"decision": "APPROVED", "reason": "Self-approval attempt."},
        ),
    ]


# ------------------------------------------------------------------ access control


def test_anonymous_requests_to_reviewer_endpoints_are_denied(
    app: Any, supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    anonymous = TestClient(app)
    for method, path, body in _all_review_requests(submission_id):
        response = anonymous.request(method, path, json=body, headers=CSRF)
        assert response.status_code == 401, (method, path)


def test_suppliers_are_denied_every_reviewer_endpoint_even_for_their_own_submission(
    supplier: TestClient, reviewer: TestClient, db: Database
) -> None:
    submission_id = _only_pending_id(reviewer)
    for method, path, body in _all_review_requests(submission_id):
        response = supplier.request(method, path, json=body, headers=CSRF)
        assert response.status_code == 403, (method, path)
        assert response.json()["code"] == "reviewer_required"
    assert _onboarding(supplier)["status"] == "PENDING_REVIEW"
    with db.session() as session:
        assert session.scalars(select(BusinessReview)).all() == []


def test_public_signup_cannot_create_a_reviewer(app: Any, db: Database) -> None:
    client = TestClient(app)
    for extra in ({"roles": ["reviewer"]}, {"is_reviewer": True}, {"role": "reviewer"}):
        assert signup(client, "sneaky@example.com", **extra).status_code == 422
    response = signup(client, "plain@example.com")
    assert response.status_code == 201
    assert response.json()["roles"] == ["supplier"]
    assert client.get("/api/v1/auth/me").json()["roles"] == ["supplier"]
    assert client.get(f"{API}/submissions").status_code == 403
    with db.session() as session:
        assert session.scalars(select(ReviewerGrant)).all() == []


def test_reviewer_role_cannot_be_escalated_through_payloads(
    supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    # Supplier payloads that try to set a status, reviewer or decision are rejected.
    for field, value in (
        ("status", "APPROVED"),
        ("reviewer_user_id", "x"),
        ("roles", ["reviewer"]),
    ):
        draft = {**FULL_DRAFT, field: value}
        assert supplier.put("/api/v1/onboarding/draft", json=draft, headers=CSRF).status_code in (
            409,
            422,
        )
    # Reviewer payloads cannot name another reviewer, supplier, status or submitted value.
    for extra in (
        {"reviewer_user_id": "someone-else"},
        {"supplier_id": "x"},
        {"status": "APPROVED"},
    ):
        assert _decide(reviewer, submission_id, "REJECTED", **extra).status_code == 422
    bad_item = {**PORTAL_CHECK["items"][0], "submitted_value": "forged"}
    assert _check(reviewer, submission_id, items=[bad_item]).status_code == 422
    assert _check(reviewer, submission_id, reviewer_user_id="x").status_code == 422
    assert supplier.get("/api/v1/auth/me").json()["roles"] == ["supplier"]


def test_a_reviewer_only_account_has_no_supplier_workspace(reviewer: TestClient) -> None:
    me = reviewer.get("/api/v1/auth/me").json()
    assert me["supplier"] is None
    assert me["roles"] == ["reviewer"]
    for path in ("/api/v1/supplier", "/api/v1/cases", "/api/v1/onboarding"):
        response = reviewer.get(path)
        assert response.status_code == 403, path
        assert response.json()["code"] == "supplier_account_required"
        assert "set-cookie" not in response.headers  # the session survives
    assert reviewer.get("/api/v1/auth/me").status_code == 200


def test_revoking_a_grant_takes_effect_on_the_next_request(
    app: Any, reviewer: TestClient, db: Database, frozen_clock: FrozenClock
) -> None:
    assert reviewer.get(f"{API}/submissions").status_code == 200
    with db.session() as session:
        reviewers.revoke_reviewer(session, frozen_clock, email=REVIEWER_EMAIL, operator="pytest")
    # A staff-only account with no grant has nothing to act on: it is signed out.
    assert reviewer.get(f"{API}/submissions").status_code == 401
    assert login(TestClient(app), REVIEWER_EMAIL).status_code == 401


def test_a_supplier_granted_the_role_keeps_their_workspace_and_loses_it_on_revoke(
    supplier: TestClient, db: Database, frozen_clock: FrozenClock
) -> None:
    with db.session() as session:
        reviewers.grant_reviewer(
            session, frozen_clock, email="owner@example.com", operator="pytest"
        )
    assert supplier.get("/api/v1/auth/me").json()["roles"] == ["supplier", "reviewer"]
    assert supplier.get(f"{API}/submissions").status_code == 200
    assert supplier.get("/api/v1/onboarding").status_code == 200
    with db.session() as session:
        reviewers.revoke_reviewer(
            session, frozen_clock, email="owner@example.com", operator="pytest"
        )
    assert supplier.get(f"{API}/submissions").status_code == 403
    assert supplier.get("/api/v1/auth/me").json()["roles"] == ["supplier"]


# ------------------------------------------------------------------ queue and detail


def test_queue_and_detail_show_the_frozen_submission(
    supplier: TestClient, reviewer: TestClient
) -> None:
    [item] = _pending(reviewer)
    assert item["udyam_number"] == UDYAM
    assert item["enterprise_name"] == "Sample Fasteners (TEST)"
    assert item["status"] == "PENDING_REVIEW"
    assert item["own_submission"] is False
    assert item["other_claimants"] == 0
    detail = reviewer.get(f"{API}/submissions/{item['submission_id']}").json()
    assert detail["profile"]["udyam_number"] == UDYAM
    assert detail["profile"]["contact_email"] == "accounts@sample.example"
    assert detail["snapshot_intact"] is True
    assert detail["certificate"]["bytes_intact"] is True
    assert detail["evidence_level"] == "supplier_submitted"
    assert detail["submitted_by"]["email"] == "owner@example.com"
    assert "Self-declared" in detail["notice"]
    assert detail["allowed_decisions"] == ["NEEDS_INFORMATION", "REJECTED"]  # no check yet
    assert detail["approval_blockers"] == [review_service.NEEDS_CHECK]
    assert [h["revision"] for h in detail["history"]] == [1]
    assert reviewer.get(f"{API}/submissions/does-not-exist").status_code == 404


def test_queue_filters_and_paginates(app: Any, reviewer: TestClient) -> None:
    for n in range(3):
        _submitted(app, f"s{n}@example.com", f"s{n}", udyam_number=f"UDYAM-MH-12-000000{n}")
    first = reviewer.get(f"{API}/submissions?limit=2").json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = reviewer.get(f"{API}/submissions?limit=2&cursor={first['next_cursor']}").json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    ids = [i["submission_id"] for i in first["items"] + second["items"]]
    assert len(set(ids)) == 3
    assert reviewer.get(f"{API}/submissions?cursor=not-a-cursor").status_code == 400
    assert reviewer.get(f"{API}/submissions?status=BOGUS").status_code == 422
    assert reviewer.get(f"{API}/submissions?status=APPROVED").json()["items"] == []
    assert len(reviewer.get(f"{API}/submissions?all=true").json()["items"]) == 3


def test_certificates_are_served_to_reviewers_only_as_attachments(
    app: Any, supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    response = reviewer.get(f"{API}/submissions/{submission_id}/certificate")
    assert response.status_code == 200
    assert response.content == pdf("owner")
    assert response.headers["content-disposition"].startswith("attachment")
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-security-policy"] == "sandbox"
    other = _supplier(app, "nosy@example.com")
    assert other.get(f"{API}/submissions/{submission_id}/certificate").status_code == 403
    certificate_id = _onboarding(supplier)["certificate"]["id"]
    owner_path = f"/api/v1/onboarding/certificates/{certificate_id}/download"
    assert other.get(owner_path).status_code == 404  # unchanged Phase 7B owner check
    assert TestClient(app).get(owner_path).status_code == 401


# ------------------------------------------------------------------ checks


def test_a_check_records_source_date_reviewer_and_snapshot_values(
    supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    response = _check(
        reviewer,
        submission_id,
        items=[
            *PORTAL_CHECK["items"],
            {"field": "address", "observed_value": "Plot 9, Elsewhere", "result": "mismatch"},
        ],
        note="Address differs on the portal.",
    )
    assert response.status_code == 201, response.text
    [check] = response.json()["checks"]
    assert check["reviewer"]["email"] == REVIEWER_EMAIL
    assert check["source"] == "udyam_portal" and check["official_source"] is True
    assert check["checked_on"] == "2026-11-01"
    assert check["recorded_at"] == NOW
    by_field = {item["field"]: item for item in check["items"]}
    assert by_field["udyam_number"]["submitted_value"] == UDYAM
    assert by_field["address"]["submitted_value"] == (
        "Plot 7, Sample Industrial Estate, Pune, Maharashtra, 411001"
    )
    assert by_field["address"]["result"] == "mismatch"
    # A mismatch means the details are reviewed but not officially corroborated.
    assert response.json()["evidence_level"] == "manually_reviewed"
    assert "APPROVED" in response.json()["allowed_decisions"]


def test_only_a_matching_official_check_counts_as_corroborated(
    supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    weak = _check(reviewer, submission_id, source="certificate_only", source_detail="The PDF")
    assert weak.json()["evidence_level"] == "manually_reviewed"
    strong = _check(reviewer, submission_id)
    assert strong.json()["evidence_level"] == "official_record_matched"
    assert len(strong.json()["checks"]) == 2  # a later check adds a row; none is replaced


@pytest.mark.parametrize(
    "changes",
    [
        {"checked_on": "2026-11-02"},  # in the future (IST date is 1 Nov)
        {"items": []},
        {"items": [{"field": "udyam_number", "result": "match"}]},  # no observed value
        {"items": [PORTAL_CHECK["items"][0], PORTAL_CHECK["items"][0]]},  # duplicate field
        {"items": [{"field": "pan", "observed_value": "x", "result": "match"}]},
        {"source": "udyam_api"},  # no such integration exists
        {"source_detail": ""},
    ],
)
def test_invalid_checks_are_rejected(
    supplier: TestClient, reviewer: TestClient, changes: dict[str, Any]
) -> None:
    assert _check(reviewer, _only_pending_id(reviewer), **changes).status_code == 422


def test_not_found_needs_no_observed_value(supplier: TestClient, reviewer: TestClient) -> None:
    items = [{"field": "udyam_number", "result": "not_found"}]
    response = _check(reviewer, _only_pending_id(reviewer), items=items)
    assert response.status_code == 201
    assert response.json()["evidence_level"] == "manually_reviewed"


# ------------------------------------------------------------------ decisions


def test_approval_needs_a_recorded_check(supplier: TestClient, reviewer: TestClient) -> None:
    submission_id = _only_pending_id(reviewer)
    response = _decide(reviewer, submission_id, "APPROVED")
    assert response.status_code == 409
    assert response.json()["code"] == "approval_blocked"
    assert _onboarding(supplier)["status"] == "PENDING_REVIEW"


def test_approve_is_final_and_hides_the_reason_and_note_from_the_supplier(
    supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    _check(reviewer, submission_id)
    response = _decide(
        reviewer,
        submission_id,
        "APPROVED",
        reason="Matched on the portal by manual lookup.",
        internal_note=INTERNAL_NOTE,
    )
    assert response.status_code == 200, response.text
    decision = response.json()["decision"]
    assert decision["reviewer"]["email"] == REVIEWER_EMAIL
    assert decision["decided_at"] == NOW
    assert decision["internal_note"] == INTERNAL_NOTE
    assert response.json()["allowed_decisions"] == []

    raw = supplier.get("/api/v1/onboarding")
    assert INTERNAL_NOTE not in raw.text and REVIEWER_EMAIL not in raw.text
    data = raw.json()
    assert data["status"] == "APPROVED" and data["editable"] is False
    assert data["latest_review"] == {
        "decision": "APPROVED",
        "reason": None,
        "decided_at": NOW,
    }
    # The supplier cannot undo or change it.
    assert (
        supplier.put("/api/v1/onboarding/draft", json=FULL_DRAFT, headers=CSRF).status_code == 409
    )
    assert supplier.post("/api/v1/onboarding/submit", headers=CSRF).status_code == 409
    # Nor can any reviewer: a decided submission takes no new decision or check.
    for decision_value in ("APPROVED", "REJECTED", "NEEDS_INFORMATION"):
        again = _decide(reviewer, submission_id, decision_value)
        assert again.status_code == 409 and again.json()["code"] == "invalid_transition"
    assert _check(reviewer, submission_id).status_code == 409
    assert (
        reviewer.get(f"{API}/submissions?status=APPROVED").json()["items"][0]["submission_id"]
        == submission_id
    )


def test_rejection_is_final_and_its_reason_reaches_the_supplier(
    supplier: TestClient, reviewer: TestClient
) -> None:
    submission_id = _only_pending_id(reviewer)
    reason = "The certificate belongs to a different enterprise."
    assert _decide(reviewer, submission_id, "REJECTED", reason=reason).status_code == 200
    data = _onboarding(supplier)
    assert data["status"] == "REJECTED" and data["editable"] is False
    assert data["latest_review"]["reason"] == reason
    assert data["submissions"][0]["review"]["decision"] == "REJECTED"
    assert supplier.post("/api/v1/onboarding/submit", headers=CSRF).status_code == 409
    assert _decide(reviewer, submission_id, "APPROVED").status_code == 409


def test_needs_information_leads_to_a_new_submission_and_keeps_the_old_one(
    supplier: TestClient, reviewer: TestClient, db: Database
) -> None:
    first_id = _only_pending_id(reviewer)
    with db.session() as session:
        before = session.get(BusinessSubmission, first_id)
        assert before is not None
        snapshot, digest = before.snapshot, before.snapshot_sha256
    response = _decide(
        reviewer, first_id, "NEEDS_INFORMATION", reason=INFO_REASON, internal_note=INTERNAL_NOTE
    )
    assert response.status_code == 200

    data = _onboarding(supplier)
    assert data["status"] == "NEEDS_INFORMATION" and data["editable"] is True
    assert data["latest_review"]["reason"] == INFO_REASON
    assert INTERNAL_NOTE not in supplier.get("/api/v1/onboarding").text
    assert reviewer.get(f"{API}/submissions").json()["items"] == []  # nothing pending now

    # The supplier corrects the draft and submits again: a second, separate submission.
    fixed = {**FULL_DRAFT, "address_line2": "Gate 2"}
    assert supplier.put("/api/v1/onboarding/draft", json=fixed, headers=CSRF).status_code == 200
    supplier.post(
        "/api/v1/onboarding/certificate",
        files={"file": ("udyam-full.pdf", pdf("owner-full"), "application/pdf")},
        headers=CSRF,
    )
    assert supplier.post("/api/v1/onboarding/submit", headers=CSRF).status_code == 200
    data = _onboarding(supplier)
    assert data["status"] == "PENDING_REVIEW" and data["latest_review"] is None
    assert [s["revision"] for s in data["submissions"]] == [2, 1]
    assert data["submissions"][1]["review"]["decision"] == "NEEDS_INFORMATION"

    second_id = _only_pending_id(reviewer)
    assert second_id != first_id
    detail = reviewer.get(f"{API}/submissions/{second_id}").json()
    assert detail["profile"]["address_line2"] == "Gate 2"
    assert [(h["revision"], h["status"]) for h in detail["history"]] == [
        (2, "PENDING_REVIEW"),
        (1, "NEEDS_INFORMATION"),
    ]
    old = reviewer.get(f"{API}/submissions/{first_id}").json()
    assert old["profile"]["address_line2"] is None  # the first snapshot is untouched
    assert old["snapshot_intact"] is True
    assert old["decision"]["reason"] == INFO_REASON
    with db.session() as session:
        after = session.get(BusinessSubmission, first_id)
        assert after is not None
        assert (after.snapshot, after.snapshot_sha256) == (snapshot, digest)
    # The old submission can no longer be decided; the new one can.
    assert _decide(reviewer, first_id, "REJECTED").status_code == 409
    assert _decide(reviewer, second_id, "REJECTED").status_code == 200


def test_decision_reasons_are_required(supplier: TestClient, reviewer: TestClient) -> None:
    submission_id = _only_pending_id(reviewer)
    assert _decide(reviewer, submission_id, "REJECTED", reason="short").status_code == 422
    assert _decide(reviewer, submission_id, "VERIFIED").status_code == 422
    assert _decide(reviewer, submission_id, "PENDING_REVIEW").status_code == 422


# ------------------------------------------------------------------ self-review


def test_a_reviewer_cannot_review_their_own_submission(
    supplier: TestClient, db: Database, frozen_clock: FrozenClock
) -> None:
    with db.session() as session:
        reviewers.grant_reviewer(
            session, frozen_clock, email="owner@example.com", operator="pytest"
        )
    [item] = supplier.get(f"{API}/submissions").json()["items"]
    assert item["own_submission"] is True
    detail = supplier.get(f"{API}/submissions/{item['submission_id']}").json()
    assert detail["own_submission"] is True and detail["allowed_decisions"] == []
    for response in (
        _decide(supplier, item["submission_id"], "REJECTED"),
        _check(supplier, item["submission_id"]),
    ):
        assert response.status_code == 403
        assert response.json()["code"] == "self_review_forbidden"
    assert _onboarding(supplier)["status"] == "PENDING_REVIEW"


# ------------------------------------------------------------------ duplicate claims


def test_duplicate_udyam_claims_are_flagged_and_settled_by_approval(
    app: Any, supplier: TestClient, reviewer: TestClient, db: Database
) -> None:
    rival = _submitted(app, "rival@example.com", "rival", enterprise_name="Rival Co (TEST)")
    items = {i["enterprise_name"]: i for i in _pending(reviewer)}
    owner_item, rival_item = items["Sample Fasteners (TEST)"], items["Rival Co (TEST)"]
    assert owner_item["other_claimants"] == 1 and rival_item["other_claimants"] == 1
    assert owner_item["claim_contested"] is False and rival_item["claim_contested"] is True
    detail = reviewer.get(f"{API}/submissions/{rival_item['submission_id']}").json()
    [other] = detail["other_claims"]
    assert other["submission_id"] == owner_item["submission_id"]
    assert other["profile_status"] == "PENDING_REVIEW"

    # The reviewer finds the second claimant is the real owner and approves it.
    _check(reviewer, rival_item["submission_id"])
    assert _decide(reviewer, rival_item["submission_id"], "APPROVED").status_code == 200
    with db.session() as session:
        claims = {
            c.supplier_id: c.contested
            for c in session.scalars(select(UdyamClaim).where(UdyamClaim.udyam_number == UDYAM))
        }
    assert claims == {
        rival_item["supplier_id"]: False,
        owner_item["supplier_id"]: True,
    }
    # The first claimant can no longer be approved for the same number.
    _check(reviewer, owner_item["submission_id"])
    blocked = reviewer.get(f"{API}/submissions/{owner_item['submission_id']}").json()
    assert review_service.ALREADY_APPROVED in blocked["approval_blockers"]
    assert "APPROVED" not in blocked["allowed_decisions"]
    response = _decide(reviewer, owner_item["submission_id"], "APPROVED")
    assert response.status_code == 409 and response.json()["code"] == "approval_blocked"
    assert _decide(reviewer, owner_item["submission_id"], "REJECTED").status_code == 200
    assert rival.get("/api/v1/onboarding").json()["status"] == "APPROVED"


# ------------------------------------------------------------------ immutability


def _raw(url: str, statement: str) -> None:
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text(statement))
    finally:
        engine.dispose()


def test_review_records_cannot_be_silently_modified(
    supplier: TestClient, reviewer: TestClient, rv_settings: Settings
) -> None:
    submission_id = _only_pending_id(reviewer)
    _check(reviewer, submission_id)
    _decide(reviewer, submission_id, "REJECTED")
    url = rv_settings.database_url
    for statement in (
        "UPDATE business_reviews SET decision = 'APPROVED'",
        "UPDATE business_reviews SET reason = 'edited'",
        "DELETE FROM business_reviews",
        "UPDATE business_checks SET source = 'other'",
        "DELETE FROM business_checks",
        "UPDATE business_check_items SET result = 'match'",
        "DELETE FROM business_check_items",
        "UPDATE business_submissions SET snapshot = '{}'",
        "DELETE FROM reviewer_grants",
        "UPDATE reviewer_grants SET user_id = 'someone-else'",
        "UPDATE reviewer_grants SET granted_by = 'forged'",
    ):
        with pytest.raises(DatabaseError):
            _raw(url, statement)
    # A grant may be revoked once, never un-revoked.
    _raw(
        url, "UPDATE reviewer_grants SET revoked_at = '2026-11-01T10:30:00.000Z', revoked_by = 'x'"
    )
    with pytest.raises(DatabaseError):
        _raw(url, "UPDATE reviewer_grants SET revoked_at = NULL")


def test_concurrent_decisions_produce_exactly_one(
    supplier: TestClient,
    reviewer: TestClient,
    db: Database,
    rv_settings: Settings,
    frozen_clock: FrozenClock,
) -> None:
    submission_id = _only_pending_id(reviewer)
    with db.session() as session:
        grant = session.scalars(select(ReviewerGrant)).one()
        principal = ReviewerPrincipal(user_id=grant.user_id, session_id="test")
    store = BusinessDocumentStore(rv_settings.storage_dir)
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def attempt(decision: str) -> None:
        database = Database(rv_settings.database_url)
        try:
            with database.session() as session:
                barrier.wait()
                try:
                    review_service.decide(
                        session,
                        frozen_clock,
                        store,
                        principal,
                        submission_id,
                        DecisionIn.model_validate(
                            {"decision": decision, "reason": "Concurrent decision test."}
                        ),
                    )
                    outcomes.append("ok")
                except Conflict:
                    outcomes.append("conflict")
        finally:
            database.dispose()

    threads = [
        threading.Thread(target=attempt, args=(d,))
        for d in ("REJECTED", "NEEDS_INFORMATION", "REJECTED", "NEEDS_INFORMATION")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["conflict", "conflict", "conflict", "ok"]
    with db.session() as session:
        assert len(session.scalars(select(BusinessReview)).all()) == 1


def test_review_writes_are_rate_limited(supplier: TestClient, reviewer: TestClient) -> None:
    submission_id = _only_pending_id(reviewer)
    assert _decide(reviewer, submission_id, "REJECTED").status_code == 200
    for _ in range(119):
        assert _check(reviewer, submission_id).status_code == 409
    response = _check(reviewer, submission_id)
    assert response.status_code == 429 and "retry-after" in response.headers


# ------------------------------------------------------------------ provisioning CLI


def test_cli_creates_lists_grants_and_revokes_reviewers(
    rv_settings: Settings,
    db: Database,
    supplier: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DATABASE_URL", rv_settings.database_url)
    for name, value in (
        ("APP_ENV", "test"),
        ("PUBLIC_BASE_URL", "http://localhost:3000"),
        ("STORAGE_DIR", str(rv_settings.storage_dir)),
        ("TOKEN_HASH_KEY", "test-only-token-hash-key-0123456789abcdef"),
        ("EMAIL_MODE", "simulated"),
    ):
        monkeypatch.setenv(name, value)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{TEST_PASSWORD}\n"))
    args = ["create", "--email", "Staff@Example.com", "--name", "Staff", "--password-stdin"]
    assert reviewer_cli.main([*args, "--operator", "ops"]) == 0
    out = capsys.readouterr().out
    assert TEST_PASSWORD not in out and "staff@example.com" in out

    monkeypatch.setattr("sys.stdin", io.StringIO(f"{TEST_PASSWORD}\n"))
    assert reviewer_cli.main(args) == 1  # duplicate email
    monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
    weak = ["create", "--email", "weak@example.com", "--name", "W", "--password-stdin"]
    assert reviewer_cli.main(weak) == 1
    assert "Not done" in capsys.readouterr().err

    assert reviewer_cli.main(["grant", "--email", "owner@example.com"]) == 0
    assert reviewer_cli.main(["grant", "--email", "owner@example.com"]) == 1  # already active
    assert reviewer_cli.main(["grant", "--email", "nobody@example.com"]) == 1
    assert reviewer_cli.main(["revoke", "--email", "owner@example.com", "--operator", "ops"]) == 0
    assert reviewer_cli.main(["revoke", "--email", "owner@example.com"]) == 1
    capsys.readouterr()
    assert reviewer_cli.main(["list"]) == 0
    listing = capsys.readouterr().out
    assert "staff@example.com\tStaff\tactive\tgranted" in listing and "staff only" in listing
    assert "owner@example.com" in listing and "revoked" in listing and "also a supplier" in listing
    assert supplier.get("/api/v1/auth/me").json()["roles"] == ["supplier"]
    with db.session() as session:
        assert len(session.scalars(select(ReviewerGrant)).all()) == 2  # both kept for audit
