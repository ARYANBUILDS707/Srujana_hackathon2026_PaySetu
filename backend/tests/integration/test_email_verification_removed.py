"""Email verification is no longer an access requirement (DECISIONS.md Section 12).

Signed-in suppliers use their own workspace straight after signup or login, whatever
`email_verified_at` says. Authentication, CSRF and ownership checks are unchanged (see
test_auth.py and test_authorisation.py). Historical verification records are kept.
"""

import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.clock import FrozenClock
from app.config import Settings
from app.db import Database
from app.main import create_app
from app.models import EmailVerificationToken, User
from tests.auth_helpers import CSRF, TEST_PASSWORD, login, outbox_messages, signup

EMAIL = "ravi.sample@example.com"
CASE = {
    "invoice_number": "INV-1",
    "invoice_date": "2026-10-01",
    "invoice_amount": "1000.00",
    "delivery_date": "2026-10-01",
    "deal_type": "verbal",
}


@pytest.fixture
def v_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def app(v_settings: Settings, frozen_clock: FrozenClock) -> Any:
    return create_app(v_settings, clock=frozen_clock)


@pytest.fixture
def client(app: Any) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(v_settings: Settings) -> Iterator[Database]:
    database = Database(v_settings.database_url)
    try:
        yield database
    finally:
        database.dispose()


def _use_workspace(client: TestClient) -> None:
    """Create a buyer and a case, then read them back: the full own-workspace path."""
    assert client.get("/api/v1/supplier").status_code == 200
    buyer = client.post("/api/v1/buyers", json={"legal_name": "Sample Buyer"}, headers=CSRF)
    assert buyer.status_code == 201
    created = client.post(
        "/api/v1/cases", json={**CASE, "buyer_id": buyer.json()["id"]}, headers=CSRF
    )
    assert created.status_code == 201
    assert [c["id"] for c in client.get("/api/v1/cases").json()] == [created.json()["id"]]
    assert client.get("/api/v1/onboarding").status_code == 200


def test_signup_opens_the_workspace_immediately(
    client: TestClient, v_settings: Settings, db: Database
) -> None:
    response = signup(client, EMAIL)
    assert response.status_code == 201
    assert response.json()["user"]["email_verified"] is False  # recorded fact, gates nothing
    _use_workspace(client)
    # No verification email is sent and no token is issued any more.
    assert outbox_messages(v_settings, EMAIL, "email_verification") == []
    with db.session() as session:
        assert session.scalars(select(EmailVerificationToken)).first() is None


def test_login_opens_the_workspace_for_an_unverified_account(
    client: TestClient, db: Database
) -> None:
    signup(client, EMAIL)
    client.cookies.clear()
    assert login(client, EMAIL).status_code == 200
    with db.session() as session:
        assert session.scalars(select(User)).one().email_verified_at is None
    _use_workspace(client)


def test_existing_unverified_accounts_keep_their_records(client: TestClient, db: Database) -> None:
    # An account from the verification era, with an unused verification link on file.
    signup(client, EMAIL)
    with db.session() as session, session.begin():
        user = session.scalars(select(User)).one()
        session.execute(
            text(
                "INSERT INTO email_verification_tokens (id, user_id, email, token_hash, "
                "created_at, expires_at) VALUES ('t-1', :uid, :email, :hash, 't', 'z')"
            ),
            {"uid": user.id, "email": EMAIL, "hash": "a" * 64},
        )
    _use_workspace(client)
    with db.session() as session:
        assert session.scalars(select(EmailVerificationToken)).one().id == "t-1"  # kept


@pytest.mark.parametrize("path", ["/api/v1/auth/verify-email", "/api/v1/auth/resend-verification"])
def test_verification_endpoints_are_gone(client: TestClient, path: str) -> None:
    signup(client, EMAIL)
    response = client.post(path, json={"token": "x"}, headers=CSRF)
    assert response.status_code in (404, 405)


def test_unauthenticated_requests_are_still_refused(app: Any) -> None:
    with TestClient(app) as anonymous:
        for path in ("/api/v1/cases", "/api/v1/supplier", "/api/v1/onboarding"):
            response = anonymous.get(path)
            assert response.status_code == 401, path
            assert response.json()["code"] == "unauthenticated"


def test_no_route_answers_email_not_verified(app: Any) -> None:
    public = {
        "/api/v1/health",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    }
    with TestClient(app) as client:
        signup(client, EMAIL)
        for path, ops in app.openapi()["paths"].items():
            if path in public:
                continue
            for method in ops:
                url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)
                response = client.request(method.upper(), url, headers=CSRF, json={})
                assert response.status_code != 403, (method, path)
                assert "email_not_verified" not in response.text


def test_a_password_reset_still_records_the_inbox_as_verified(
    client: TestClient, v_settings: Settings, db: Database
) -> None:
    # Unchanged Phase 6.1 / 7A behaviour of the reset flow.
    signup(client, EMAIL)
    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL}, headers=CSRF)
    message = outbox_messages(v_settings, EMAIL, "password_reset")[-1].get_content()
    token = re.search(r"#token=([A-Za-z0-9_-]+)", message)
    assert token
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token.group(1), "new_password": "another-sample-passphrase"},
        headers=CSRF,
    )
    assert response.status_code == 200
    with db.session() as session:
        assert session.scalars(select(User)).one().email_verified_at is not None
    client.cookies.clear()
    assert login(client, EMAIL, "another-sample-passphrase").status_code == 200
    assert login(client, EMAIL, TEST_PASSWORD).status_code == 401
