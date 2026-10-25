"""Phase 7A: email verification, resend, the verified-email access policy and migration."""

import io
import json
import logging
import re
import threading
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from app.clock import FrozenClock, format_utc_timestamp
from app.config import Settings
from app.db import Database
from app.errors import BadRequest
from app.logging import LOGGER_NAME, JsonFormatter
from app.mail.senders import EmailDeliveryError, OutgoingEmail
from app.main import create_app
from app.models import EmailVerificationToken, User
from app.services import auth as auth_service
from seed.demo import seed
from tests.auth_helpers import (
    CSRF,
    TEST_PASSWORD,
    latest_verification_token,
    login,
    outbox_messages,
    signup,
    verify_email,
)
from tests.conftest import alembic_config

EMAIL = "ravi.sample@example.com"
OTHER = "other.sample@example.com"


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


def _me(client: TestClient) -> Any:
    return client.get("/api/v1/auth/me").json()


def _verify(client: TestClient, token: str) -> Any:
    return client.post("/api/v1/auth/verify-email", json={"token": token}, headers=CSRF)


def _resend(client: TestClient) -> Any:
    return client.post("/api/v1/auth/resend-verification", headers=CSRF)


class FailingSender:
    mode = "test"

    def __init__(self) -> None:
        self.sent: list[OutgoingEmail] = []

    def send(self, message: OutgoingEmail) -> None:
        self.sent.append(message)
        raise EmailDeliveryError("provider unavailable (test)")


# --------------------------------------------------------------------------- signup


def test_signup_creates_an_unverified_user_and_emails_a_link(
    client: TestClient, v_settings: Settings, db: Database
) -> None:
    response = signup(client, EMAIL)
    assert response.status_code == 201
    assert response.json()["user"]["email_verified"] is False
    assert _me(client)["user"]["email_verified"] is False

    messages = outbox_messages(v_settings, EMAIL, "email_verification")
    assert len(messages) == 1
    body = messages[0].get_content()
    assert "http://localhost:3000/verify-email#token=" in body  # PUBLIC_BASE_URL, fragment
    assert "24 hours" in body and "does not verify your business" in body
    token = latest_verification_token(v_settings, EMAIL)
    assert token not in response.text

    with db.session() as session:
        user = session.scalars(select(User)).one()
        row = session.scalars(select(EmailVerificationToken)).one()
    assert user.email_verified_at is None
    assert row.token_hash != token and len(row.token_hash) == 64 and row.email == EMAIL
    assert row.used_at is None and row.revoked_at is None


def test_links_use_the_configured_origin_not_the_request_host(
    client: TestClient, v_settings: Settings
) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Sample User",
            "business_name": "Sample Traders (TEST)",
            "email": EMAIL,
            "password": TEST_PASSWORD,
            "accept_terms_version": "evaluation-2026-10",
        },
        headers={**CSRF, "Host": "evil.example", "X-Forwarded-Host": "evil.example"},
    )
    body = outbox_messages(v_settings, EMAIL, "email_verification")[0].get_content()
    assert "evil.example" not in body and "http://localhost:3000/verify-email#" in body


# ------------------------------------------------------------------------- verify


def test_a_valid_link_verifies_the_email_and_opens_the_workspace(
    client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    assert client.get("/api/v1/cases").status_code == 403
    response = _verify(client, latest_verification_token(v_settings, EMAIL))
    assert response.status_code == 200 and response.json() == {"email_verified": True}
    assert response.headers["cache-control"] == "no-store"
    assert _me(client)["user"]["email_verified"] is True
    assert client.get("/api/v1/cases").status_code == 200  # same session, now allowed


def test_verification_works_without_a_session_and_signs_no_one_in(
    app: Any, client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    token = latest_verification_token(v_settings, EMAIL)
    with TestClient(app) as phone:  # the link opened on another device, signed out
        response = _verify(phone, token)
        assert response.status_code == 200
        assert "set-cookie" not in response.headers
        assert phone.get("/api/v1/auth/me").status_code == 401
    assert _me(client)["user"]["email_verified"] is True


@pytest.mark.parametrize("token", ["not-a-real-token", "x" * 128])
def test_invalid_tokens_are_rejected(client: TestClient, token: str) -> None:
    signup(client, EMAIL)
    response = _verify(client, token)
    assert response.status_code == 400 and response.json()["code"] == "invalid_verification_token"
    assert response.json()["detail"] == auth_service.INVALID_VERIFICATION_TOKEN
    assert _me(client)["user"]["email_verified"] is False


def test_oversized_tokens_fail_validation(client: TestClient) -> None:
    assert _verify(client, "x" * 129).status_code == 422


def test_a_used_link_cannot_be_used_again(client: TestClient, v_settings: Settings) -> None:
    signup(client, EMAIL)
    token = latest_verification_token(v_settings, EMAIL)
    assert _verify(client, token).status_code == 200
    again = _verify(client, token)
    assert again.status_code == 400 and again.json()["code"] == "invalid_verification_token"


def test_links_expire_after_24_hours(
    client: TestClient, v_settings: Settings, frozen_clock: FrozenClock
) -> None:
    signup(client, EMAIL)
    token = latest_verification_token(v_settings, EMAIL)
    frozen_clock.advance(timedelta(hours=24))
    expired = _verify(client, token)
    assert expired.status_code == 400 and expired.json()["code"] == "invalid_verification_token"
    assert _me(client)["user"]["email_verified"] is False

    frozen_clock.advance(timedelta(minutes=1))
    assert _resend(client).json()["notification"] == "sent"
    fresh = latest_verification_token(v_settings, EMAIL)
    frozen_clock.advance(timedelta(hours=23, minutes=59))
    assert _verify(client, fresh).status_code == 200  # still inside 24 hours


def test_expiry_is_configurable(v_settings: Settings, frozen_clock: FrozenClock) -> None:
    short = v_settings.model_copy(update={"email_verification_hours": 1})
    with TestClient(create_app(short, clock=frozen_clock)) as client:
        signup(client, EMAIL)
        token = latest_verification_token(short, EMAIL)
        frozen_clock.advance(timedelta(hours=1))
        assert _verify(client, token).status_code == 400


def test_concurrent_verifications_with_one_token_succeed_exactly_once(
    client: TestClient, v_settings: Settings, frozen_clock: FrozenClock
) -> None:
    signup(client, EMAIL)
    token = latest_verification_token(v_settings, EMAIL)
    barrier = threading.Barrier(4)
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        database = Database(v_settings.database_url)
        try:
            barrier.wait()
            with database.session() as session:
                auth_service.verify_email(session, frozen_clock, v_settings, token)
            result = "ok"
        except BadRequest:
            result = "rejected"
        finally:
            database.dispose()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["ok", "rejected", "rejected", "rejected"]
    assert _me(client)["user"]["email_verified"] is True


def test_a_token_verifies_only_its_own_account(
    app: Any, client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    with TestClient(app) as other:
        signup(other, OTHER)
        # B, signed in, uses A's link: A is verified, B is not.
        assert _verify(other, latest_verification_token(v_settings, EMAIL)).status_code == 200
        assert _me(other)["user"]["email_verified"] is False
        assert other.get("/api/v1/cases").status_code == 403
    assert _me(client)["user"]["email_verified"] is True


def test_a_link_stops_working_if_the_address_changes(
    client: TestClient, v_settings: Settings, db: Database
) -> None:
    signup(client, EMAIL)
    token = latest_verification_token(v_settings, EMAIL)
    with db.session() as session, session.begin():  # no email-change feature exists yet
        session.scalars(select(User)).one().email = "changed@example.com"
    assert _verify(client, token).status_code == 400
    assert _me(client)["user"]["email_verified"] is False


def test_verification_grants_nothing_beyond_the_flag(
    client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    before = _me(client)
    verify_email(client, v_settings, EMAIL)
    after = _me(client)
    before["user"]["email_verified"] = True
    assert after == before  # same user, same supplier; no role or other field changed
    assert after["supplier"]["demo_mode"] is False


def test_verify_email_is_rate_limited_per_source_and_needs_csrf(client: TestClient) -> None:
    assert client.post("/api/v1/auth/verify-email", json={"token": "x"}).status_code == 403
    codes = [_verify(client, f"guess-{n}").status_code for n in range(121)]
    assert codes == [400] * 120 + [429]


# ------------------------------------------------------------------------- resend


def test_resend_replaces_the_previous_link(client: TestClient, v_settings: Settings) -> None:
    signup(client, EMAIL)
    first = latest_verification_token(v_settings, EMAIL)
    response = _resend(client)
    assert response.status_code == 200
    assert response.json() == {"notification": "sent", "retry_after_seconds": 60}
    second = latest_verification_token(v_settings, EMAIL)
    assert first != second and second not in response.text
    assert _verify(client, first).status_code == 400  # superseded
    assert _verify(client, second).status_code == 200


def test_resend_has_a_cooldown_and_an_hourly_limit(
    client: TestClient, frozen_clock: FrozenClock
) -> None:
    signup(client, EMAIL)
    assert _resend(client).status_code == 200
    too_soon = _resend(client)
    assert too_soon.status_code == 429 and 0 < int(too_soon.headers["retry-after"]) <= 60
    codes = []
    for _ in range(5):
        frozen_clock.advance(timedelta(seconds=61))
        codes.append(_resend(client).status_code)
    assert codes == [200, 200, 200, 200, 429]  # five per hour in total


def test_resend_needs_a_session_and_csrf_and_an_unverified_email(
    client: TestClient, v_settings: Settings
) -> None:
    assert _resend(client).status_code == 401
    signup(client, EMAIL)
    assert client.post("/api/v1/auth/resend-verification").status_code == 403
    verify_email(client, v_settings, EMAIL)
    done = _resend(client)
    assert done.status_code == 409 and done.json()["code"] == "already_verified"


def test_resend_only_ever_emails_the_callers_own_address(
    client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    rejected = client.post("/api/v1/auth/resend-verification", json={"email": OTHER}, headers=CSRF)
    assert rejected.status_code == 200  # the body is ignored: there is no email parameter
    assert outbox_messages(v_settings, OTHER, "email_verification") == []
    assert len(outbox_messages(v_settings, EMAIL, "email_verification")) == 2


# ---------------------------------------------------------------- delivery failures


def test_failed_delivery_is_reported_honestly_and_the_link_revoked(
    app: Any, client: TestClient, db: Database
) -> None:
    failing = FailingSender()
    app.state.email_sender = failing
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        created = signup(client, EMAIL)  # delivery fails after the response
        resent = _resend(client)
    finally:
        logger.removeHandler(handler)
    assert created.status_code == 201  # the account exists; the user can resend
    assert resent.status_code == 200 and resent.json()["notification"] == "failed"

    tokens = [re.search(r"#token=([A-Za-z0-9_-]+)", m.body) for m in failing.sent]
    assert len(tokens) == 2 and all(tokens)
    with db.session() as session:
        rows = session.scalars(select(EmailVerificationToken)).all()
    assert len(rows) == 2 and all(r.revoked_at is not None for r in rows)
    for match in tokens:
        assert match is not None
        assert _verify(client, match.group(1)).status_code == 400  # undelivered = dead

    logged = buffer.getvalue()
    for match in tokens:
        assert match is not None and match.group(1) not in logged
    assert EMAIL not in logged
    failures = [
        json.loads(line)
        for line in logged.splitlines()
        if json.loads(line).get("event") == "email_delivery"
    ]
    assert [(f["kind"], f["outcome"]) for f in failures] == [
        ("email_verification", "failed"),
        ("email_verification", "failed"),
    ]


# ------------------------------------------------------------------ access policy


def test_unverified_users_keep_account_functions_but_not_the_workspace(
    app: Any, client: TestClient, v_settings: Settings
) -> None:
    signup(client, EMAIL)
    workspace = [
        ("GET", "/api/v1/supplier"),
        ("GET", "/api/v1/buyers"),
        ("POST", "/api/v1/buyers"),
        ("GET", "/api/v1/cases"),
        ("POST", "/api/v1/cases"),
    ]
    for method, path in workspace:
        response = client.request(method, path, headers=CSRF, json={"legal_name": "x"})
        assert response.status_code == 403, (method, path)
        assert response.json()["code"] == "email_not_verified"

    # Account functions stay available while unverified.
    assert client.get("/api/v1/auth/me").status_code == 200
    assert _resend(client).status_code == 200
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "another-sample-passphrase"},
        headers=CSRF,
    )
    assert changed.status_code == 200
    forgot = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL}, headers=CSRF)
    assert forgot.status_code == 202
    assert client.post("/api/v1/auth/logout-all", headers=CSRF).status_code == 204


def test_every_workspace_operation_requires_a_verified_email(
    app: Any, v_settings: Settings
) -> None:
    account_or_public = {
        "/api/v1/health",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/change-password",
        "/api/v1/auth/logout-all",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
    }
    operations = [
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if path not in account_or_public
    ]
    assert len(operations) >= 17
    with TestClient(app) as client:
        signup(client, EMAIL)
        for method, path in operations:
            url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)
            response = client.request(method, url, headers=CSRF, json={})
            assert response.status_code == 403, (method, path, response.status_code)
            assert response.json()["code"] == "email_not_verified"


def test_a_password_reset_also_proves_the_inbox(client: TestClient, v_settings: Settings) -> None:
    signup(client, EMAIL)
    client.post("/api/v1/auth/forgot-password", json={"email": EMAIL}, headers=CSRF)
    reset = outbox_messages(v_settings, EMAIL, "password_reset")[-1].get_content()
    token = re.search(r"#token=([A-Za-z0-9_-]+)", reset)
    assert token
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token.group(1), "new_password": "another-sample-passphrase"},
        headers=CSRF,
    )
    assert response.status_code == 200
    client.cookies.clear()
    login(client, EMAIL, "another-sample-passphrase")
    assert _me(client)["user"]["email_verified"] is True
    pending = latest_verification_token(v_settings, EMAIL)
    assert _verify(client, pending).status_code == 400  # outstanding link no longer needed


# --------------------------------------------------------------- existing accounts


def test_existing_accounts_stay_unverified_after_the_migration(
    migrated_database_url: str,
) -> None:
    config = alembic_config(migrated_database_url)
    command.downgrade(config, "d71bd50903a9")
    engine = create_engine(migrated_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, terms_version, "
                    "terms_accepted_at, is_active, created_at, updated_at) VALUES ('u-1', "
                    "'old@example.com', 'x', 'Existing User', 'evaluation-2026-10', 't', 1, "
                    "'t', 't')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO sessions (id, user_id, token_hash, created_at, last_seen_at, "
                    "expires_at) VALUES ('s-1', 'u-1', 'h', 't', 't', 't')"
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            user = connection.execute(text("SELECT email, email_verified_at FROM users")).one()
            sessions = connection.execute(text("SELECT count(*) FROM sessions")).scalar_one()
    finally:
        engine.dispose()
    assert tuple(user) == ("old@example.com", None)  # not trusted automatically
    assert sessions == 1  # not signed out either


def test_demo_account_is_unverified_unless_explicitly_requested(
    v_settings: Settings, frozen_clock: FrozenClock, db: Database
) -> None:
    with db.session() as session:
        seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    with db.session() as session:
        auth_service.create_demo_account(
            session, frozen_clock, "demo@paysetu.example", TEST_PASSWORD
        )
    with db.session() as session:
        user = session.scalars(select(User)).one()
    assert user.email_verified_at is None


def test_an_existing_unverified_user_verifies_by_signing_in_and_resending(
    client: TestClient, v_settings: Settings, db: Database
) -> None:
    signup(client, EMAIL)
    with db.session() as session, session.begin():  # as if created before Phase 7A
        session.execute(text("DELETE FROM email_verification_tokens"))
    client.cookies.clear()
    assert login(client, EMAIL).status_code == 200
    assert _me(client)["user"]["email_verified"] is False
    assert _resend(client).json()["notification"] == "sent"
    verify_email(client, v_settings, EMAIL)
    assert client.get("/api/v1/cases").status_code == 200
