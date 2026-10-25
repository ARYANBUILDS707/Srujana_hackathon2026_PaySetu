"""Phase 6.1: forgot/reset password, change password, sign out everywhere, email delivery."""

import io
import json
import logging
import re
import smtplib
import stat
import threading
from collections.abc import Iterator
from datetime import timedelta
from email import message_from_bytes, policy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.clock import FrozenClock
from app.config import EmailMode, Settings
from app.db import Database
from app.errors import BadRequest
from app.logging import LOGGER_NAME, JsonFormatter
from app.mail.senders import (
    EmailDeliveryError,
    FileOutboxSender,
    OutgoingEmail,
    SmtpSender,
    build_sender,
)
from app.main import create_app
from app.models import PasswordResetToken, User
from app.schemas.auth import ResetPasswordIn
from app.security.sessions import SESSION_COOKIE
from app.services import auth as auth_service
from tests.auth_helpers import CSRF, TEST_PASSWORD, login, signup

EMAIL = "ravi.sample@example.com"
OTHER = "other.sample@example.com"
NEW_PASSWORD = "brand-new-sample-passphrase"
TOKEN_IN_LINK = re.compile(r"/reset-password#token=([A-Za-z0-9_-]+)")


@pytest.fixture
def pw_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def app(pw_settings: Settings, frozen_clock: FrozenClock) -> Any:
    return create_app(pw_settings, clock=frozen_clock)


@pytest.fixture
def client(app: Any) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(pw_settings: Settings) -> Iterator[Database]:
    database = Database(pw_settings.database_url)
    try:
        yield database
    finally:
        database.dispose()


def _outbox(settings: Settings) -> list[Any]:
    folder = Path(settings.storage_dir) / "outbox"
    if not folder.exists():
        return []
    return [
        message_from_bytes(p.read_bytes(), policy=policy.default)
        for p in sorted(folder.glob("*.eml"))
    ]


def _mail_to(settings: Settings, email: str, kind: str) -> list[Any]:
    return [m for m in _outbox(settings) if m["To"] == email and m["X-PaySetu-Kind"] == kind]


def _forgot(client: TestClient, email: str = EMAIL) -> Any:
    return client.post("/api/v1/auth/forgot-password", json={"email": email}, headers=CSRF)


def _reset(client: TestClient, token: str, password: str = NEW_PASSWORD) -> Any:
    return client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": password},
        headers=CSRF,
    )


def _latest_token(settings: Settings, email: str = EMAIL) -> str:
    message = _mail_to(settings, email, "password_reset")[-1]
    match = TOKEN_IN_LINK.search(message.get_content())
    assert match, "reset link not found"
    return match.group(1)


def _registered(client: TestClient, email: str = EMAIL) -> None:
    assert signup(client, email).status_code == 201


class RecordingSender:
    """Captures messages; optionally fails after capturing (to test delivery failures)."""

    mode = "test"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[OutgoingEmail] = []

    def send(self, message: OutgoingEmail) -> None:
        self.sent.append(message)
        if self.fail:
            raise EmailDeliveryError("provider unavailable (test)")


# ---------------------------------------------------------------------- forgot password


def test_forgot_password_emails_a_single_use_link_and_stores_only_a_hash(
    client: TestClient, pw_settings: Settings, db: Database
) -> None:
    _registered(client)
    response = _forgot(client)
    assert response.status_code == 202
    assert response.headers["cache-control"] == "no-store"
    token = _latest_token(pw_settings)
    assert token not in response.text
    link = TOKEN_IN_LINK.search(_mail_to(pw_settings, EMAIL, "password_reset")[0].get_content())
    assert link and "http://localhost:3000/reset-password#token=" in link.string
    assert "15 minutes" in _mail_to(pw_settings, EMAIL, "password_reset")[0].get_content()
    with db.session() as session:
        row = session.scalars(select(PasswordResetToken)).one()
    assert row.token_hash != token and token not in row.token_hash and len(row.token_hash) == 64
    assert row.used_at is None and row.revoked_at is None
    outbox = Path(pw_settings.storage_dir) / "outbox"
    assert stat.S_IMODE(outbox.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in outbox.glob("*.eml"))


def test_unknown_and_known_emails_get_identical_answers(
    client: TestClient, pw_settings: Settings, db: Database
) -> None:
    _registered(client)
    known = _forgot(client, EMAIL)
    unknown = _forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert "If an account exists" in known.json()["detail"]
    assert set(known.headers) == set(unknown.headers)  # header names, not request IDs
    assert _mail_to(pw_settings, "nobody@example.com", "password_reset") == []
    with db.session() as session:
        assert len(session.scalars(select(PasswordResetToken)).all()) == 1


def test_inactive_accounts_get_no_email(
    client: TestClient, pw_settings: Settings, db: Database
) -> None:
    _registered(client)
    with db.session() as session, session.begin():
        session.scalars(select(User)).one().is_active = False
    assert _forgot(client).status_code == 202
    assert _mail_to(pw_settings, EMAIL, "password_reset") == []


def test_a_new_request_revokes_the_previous_unused_token(
    client: TestClient, pw_settings: Settings
) -> None:
    _registered(client)
    _forgot(client)
    first = _latest_token(pw_settings)
    _forgot(client)
    second = _latest_token(pw_settings)
    assert first != second
    assert _reset(client, first).status_code == 400
    assert _reset(client, second).status_code == 200


def test_forgot_password_is_rate_limited_per_account_and_source(client: TestClient) -> None:
    codes = [_forgot(client, EMAIL).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]  # 3/hour per IP + email (unknown email too)
    other = [_forgot(client, f"u{n}@example.com").status_code for n in range(8)]
    assert other == [202] * 6 + [429, 429]  # 10/hour per IP in total


def test_forgot_password_needs_csrf_headers(client: TestClient) -> None:
    response = client.post("/api/v1/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 403


# ----------------------------------------------------------------------- reset password


def test_reset_sets_the_password_signs_out_everywhere_and_notifies(
    app: Any, client: TestClient, pw_settings: Settings
) -> None:
    _registered(client)  # this client now holds a session
    with TestClient(app) as other_device:
        assert login(other_device, EMAIL).status_code == 200
        _forgot(other_device)
        token = _latest_token(pw_settings)
        response = _reset(other_device, token)
        assert response.status_code == 200 and response.json() == {"notification": "sent"}
        assert "Max-Age=0" in response.headers["set-cookie"]  # not signed in afterwards
        assert other_device.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401  # every old session revoked
    client.cookies.clear()
    assert login(client, EMAIL, TEST_PASSWORD).status_code == 401
    assert login(client, EMAIL, NEW_PASSWORD).status_code == 200
    notice = _mail_to(pw_settings, EMAIL, "password_changed")
    assert len(notice) == 1 and "reset with an emailed link" in notice[0].get_content()
    assert token not in notice[0].get_content()


def test_a_used_token_cannot_be_used_again(client: TestClient, pw_settings: Settings) -> None:
    _registered(client)
    _forgot(client)
    token = _latest_token(pw_settings)
    assert _reset(client, token).status_code == 200
    again = _reset(client, token, "another-sample-passphrase")
    assert again.status_code == 400 and again.json()["code"] == "invalid_reset_token"
    client.cookies.clear()
    assert login(client, EMAIL, NEW_PASSWORD).status_code == 200  # unchanged by the replay


def test_tokens_expire_after_15_minutes(
    client: TestClient, pw_settings: Settings, frozen_clock: FrozenClock
) -> None:
    _registered(client)
    _forgot(client)
    early = _latest_token(pw_settings)
    frozen_clock.advance(timedelta(minutes=14, seconds=59))
    assert _reset(client, early).status_code == 200

    _forgot(client)
    late = _latest_token(pw_settings)
    frozen_clock.advance(timedelta(minutes=15))
    expired = _reset(client, late, "another-sample-passphrase")
    assert expired.status_code == 400 and expired.json()["code"] == "invalid_reset_token"


@pytest.mark.parametrize("token", ["not-a-real-token", "x" * 128, "x" * 129])
def test_invalid_tokens_are_rejected_with_one_generic_message(
    client: TestClient, token: str
) -> None:
    _registered(client)
    response = _reset(client, token)
    assert response.status_code in (400, 422)
    if response.status_code == 400:
        assert response.json()["detail"] == auth_service.INVALID_RESET_TOKEN


@pytest.mark.parametrize(
    "password", ["short-1", "Password123", "x" * 129], ids=["short", "common", "long"]
)
def test_reset_enforces_the_password_policy_without_using_up_the_token(
    client: TestClient, pw_settings: Settings, password: str
) -> None:
    _registered(client)
    _forgot(client)
    token = _latest_token(pw_settings)
    weak = _reset(client, token, password)
    assert weak.status_code == 422 and "new_password" in {e["field"] for e in weak.json()["errors"]}
    assert password not in weak.text and token not in weak.text
    assert _reset(client, token).status_code == 200  # the token was not consumed


def test_concurrent_resets_with_one_token_succeed_exactly_once(
    client: TestClient, pw_settings: Settings, frozen_clock: FrozenClock
) -> None:
    _registered(client)
    _forgot(client)
    token = _latest_token(pw_settings)
    barrier = threading.Barrier(4)
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt(n: int) -> None:
        database = Database(pw_settings.database_url)
        try:
            data = ResetPasswordIn(token=token, new_password=f"racing-sample-passphrase-{n}")
            barrier.wait()
            with database.session() as session:
                auth_service.reset_password(session, frozen_clock, pw_settings, data)
            result = f"ok-{n}"
        except BadRequest:
            result = "rejected"
        finally:
            database.dispose()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    winners = [o for o in outcomes if o.startswith("ok")]
    assert len(winners) == 1 and outcomes.count("rejected") == 3
    client.cookies.clear()
    winner = winners[0].removeprefix("ok-")
    assert login(client, EMAIL, f"racing-sample-passphrase-{winner}").status_code == 200


def test_reset_is_rate_limited_per_source(client: TestClient) -> None:
    codes = [_reset(client, f"guess-{n}").status_code for n in range(11)]
    assert codes == [400] * 10 + [429]


def test_a_token_only_ever_changes_its_own_account(
    app: Any, client: TestClient, pw_settings: Settings
) -> None:
    _registered(client, EMAIL)
    with TestClient(app) as other:
        _registered(other, OTHER)
        _forgot(client, EMAIL)
        assert _reset(client, _latest_token(pw_settings, EMAIL)).status_code == 200
        assert other.get("/api/v1/auth/me").status_code == 200  # B is still signed in
        other.cookies.clear()
        assert login(other, OTHER, TEST_PASSWORD).status_code == 200  # B's password unchanged
        assert login(other, OTHER, NEW_PASSWORD).status_code == 401


# -------------------------------------------------------------------- email delivery


def test_failed_reset_email_is_not_reported_and_its_token_is_revoked(
    app: Any, client: TestClient, db: Database
) -> None:
    _registered(client)
    failing = RecordingSender(fail=True)
    app.state.email_sender = failing
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        failed = _forgot(client)
        unknown = _forgot(client, "nobody@example.com")
    finally:
        logger.removeHandler(handler)
    assert failed.status_code == unknown.status_code == 202
    assert failed.json() == unknown.json()  # no difference visible to the caller

    token = TOKEN_IN_LINK.search(failing.sent[0].body)
    assert token
    with db.session() as session:
        row = session.scalars(select(PasswordResetToken)).one()
    assert row.revoked_at is not None  # the undelivered link is dead
    assert _reset(client, token.group(1)).status_code == 400

    entries = [json.loads(line) for line in buffer.getvalue().splitlines()]
    delivery = [e for e in entries if e.get("event") == "email_delivery"]
    assert delivery and delivery[0]["outcome"] == "failed"
    assert delivery[0]["kind"] == "password_reset" and delivery[0]["user_id"]
    logged = buffer.getvalue()
    assert token.group(1) not in logged and EMAIL not in logged


def test_change_password_reports_a_failed_notification_honestly(
    app: Any, client: TestClient
) -> None:
    _registered(client)
    app.state.email_sender = RecordingSender(fail=True)
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        headers=CSRF,
    )
    assert response.status_code == 200 and response.json() == {"notification": "failed"}
    client.cookies.clear()
    assert login(client, EMAIL, NEW_PASSWORD).status_code == 200  # the change still happened


def test_smtp_sender_uses_configured_settings(
    pw_settings: Settings, frozen_clock: FrozenClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(f"connect {host}:{port} timeout={timeout}")

        def __enter__(self) -> "FakeSmtp":
            return self

        def __exit__(self, *args: object) -> None:
            calls.append("quit")

        def starttls(self, context: object) -> None:
            calls.append("starttls")

        def login(self, user: str, password: str) -> None:
            calls.append(f"login {user}")

        def send_message(self, message: Any) -> None:
            calls.append(f"send to {message['To']} from {message['From']}")

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    smtp_settings = pw_settings.model_copy(
        update={
            "email_mode": EmailMode.SMTP,
            "smtp_host": "smtp.example",
            "smtp_port": 2525,
            "smtp_username": "mailer",
            "smtp_password": pw_settings.token_hash_key,  # any SecretStr placeholder
            "email_from": "PaySetu <noreply@paysetu.example>",
        }
    )
    sender = build_sender(smtp_settings, frozen_clock)
    assert isinstance(sender, SmtpSender)
    sender.send(OutgoingEmail(EMAIL, "Subject", "Body", "password_changed"))
    assert calls == [
        "connect smtp.example:2525 timeout=15",
        "starttls",
        "login mailer",
        f"send to {EMAIL} from PaySetu <noreply@paysetu.example>",
        "quit",
    ]

    class BrokenSmtp(FakeSmtp):
        def send_message(self, message: Any) -> None:
            raise smtplib.SMTPRecipientsRefused({EMAIL: (550, b"no")})

    monkeypatch.setattr(smtplib, "SMTP", BrokenSmtp)
    with pytest.raises(EmailDeliveryError, match="SMTPRecipientsRefused") as info:
        sender.send(OutgoingEmail(EMAIL, "Subject", "Body", "password_changed"))
    assert EMAIL not in str(info.value)


def test_file_outbox_withholds_bodies_in_production_and_reports_write_failures(
    tmp_path: Path, frozen_clock: FrozenClock
) -> None:
    production = FileOutboxSender(
        tmp_path / "outbox", "x@paysetu.invalid", frozen_clock, withhold_body=True
    )
    production.send(OutgoingEmail(EMAIL, "Reset", "secret-link-token", "password_reset"))
    content = next((tmp_path / "outbox").glob("*.eml")).read_bytes()
    assert b"secret-link-token" not in content and b"Body withheld" in content

    blocked = tmp_path / "not-a-dir"
    blocked.write_text("file in the way")
    broken = FileOutboxSender(blocked, "x@paysetu.invalid", frozen_clock, withhold_body=False)
    with pytest.raises(EmailDeliveryError, match="outbox write failed"):
        broken.send(OutgoingEmail(EMAIL, "Reset", "body", "password_reset"))


# ---------------------------------------------------------------------- change password


def _change(client: TestClient, current: str, new: str) -> Any:
    return client.post(
        "/api/v1/auth/change-password",
        json={"current_password": current, "new_password": new},
        headers=CSRF,
    )


def test_change_password_keeps_this_browser_signed_in_on_a_new_session(
    app: Any, client: TestClient, pw_settings: Settings
) -> None:
    _registered(client)
    old_cookie = client.cookies[SESSION_COOKIE]
    with TestClient(app) as other_device:
        assert login(other_device, EMAIL).status_code == 200
        _forgot(other_device)  # an outstanding reset link
        pending = _latest_token(pw_settings)

        response = _change(client, TEST_PASSWORD, NEW_PASSWORD)
        assert response.status_code == 200 and response.json() == {"notification": "sent"}
        assert "HttpOnly" in response.headers["set-cookie"]
        assert client.cookies[SESSION_COOKIE] != old_cookie
        assert client.get("/api/v1/auth/me").status_code == 200  # still signed in
        assert other_device.get("/api/v1/auth/me").status_code == 401  # others revoked

    client.cookies.set(SESSION_COOKIE, old_cookie)
    assert client.get("/api/v1/auth/me").status_code == 401  # the old token is dead too
    assert _reset(client, pending).status_code == 400  # outstanding reset links revoked
    client.cookies.clear()
    assert login(client, EMAIL, TEST_PASSWORD).status_code == 401
    assert login(client, EMAIL, NEW_PASSWORD).status_code == 200
    notice = _mail_to(pw_settings, EMAIL, "password_changed")
    assert len(notice) == 1 and "changed from your account" in notice[0].get_content()


def test_change_password_rejects_a_wrong_current_password(client: TestClient) -> None:
    _registered(client)
    response = _change(client, "not-my-current-passphrase", NEW_PASSWORD)
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "current_password"
    assert client.get("/api/v1/auth/me").status_code == 200  # still signed in
    client.cookies.clear()
    assert login(client, EMAIL, TEST_PASSWORD).status_code == 200  # unchanged


def test_change_password_rejects_reusing_the_current_password(client: TestClient) -> None:
    _registered(client)
    response = _change(client, TEST_PASSWORD, TEST_PASSWORD)
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "new_password"


@pytest.mark.parametrize("password", ["short-1", "qwerty12345"])
def test_change_password_enforces_the_policy(client: TestClient, password: str) -> None:
    _registered(client)
    response = _change(client, TEST_PASSWORD, password)
    assert response.status_code == 422
    assert "new_password" in {e["field"] for e in response.json()["errors"]}
    assert password not in response.text and TEST_PASSWORD not in response.text


def test_change_password_needs_a_session_and_csrf(client: TestClient) -> None:
    anonymous = _change(client, TEST_PASSWORD, NEW_PASSWORD)
    assert anonymous.status_code == 401
    _registered(client)
    no_csrf = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert no_csrf.status_code == 403


def test_change_password_attempts_are_rate_limited_per_user(client: TestClient) -> None:
    _registered(client)
    codes = [_change(client, f"wrong-passphrase-{n}", NEW_PASSWORD).status_code for n in range(6)]
    assert codes == [422] * 5 + [429]


# ---------------------------------------------------------------------- sign out everywhere


def test_logout_all_revokes_every_session_of_the_user_only(app: Any, client: TestClient) -> None:
    _registered(client)
    old_cookie = client.cookies[SESSION_COOKIE]
    with TestClient(app) as laptop, TestClient(app) as stranger:
        assert login(laptop, EMAIL).status_code == 200
        _registered(stranger, OTHER)
        response = client.post("/api/v1/auth/logout-all", headers=CSRF)
        assert response.status_code == 204 and "Max-Age=0" in response.headers["set-cookie"]
        assert laptop.get("/api/v1/auth/me").status_code == 401
        assert stranger.get("/api/v1/auth/me").status_code == 200  # other users untouched
    client.cookies.set(SESSION_COOKIE, old_cookie)
    assert client.get("/api/v1/auth/me").status_code == 401  # cannot be reused
    client.cookies.clear()
    assert login(client, EMAIL).status_code == 200  # signing in again works


def test_logout_all_needs_a_session_and_csrf(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout-all", headers=CSRF).status_code == 401
    _registered(client)
    assert client.post("/api/v1/auth/logout-all").status_code == 403


# ----------------------------------------------------------------------- secrets in logs


def test_no_token_password_or_address_reaches_the_logs(
    client: TestClient, pw_settings: Settings
) -> None:
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        _registered(client)
        _forgot(client)
        token = _latest_token(pw_settings)
        _reset(client, token)
        login(client, EMAIL, NEW_PASSWORD)
        _change(client, NEW_PASSWORD, "third-sample-passphrase")
    finally:
        logger.removeHandler(handler)
    logged = buffer.getvalue()
    for secret in (token, TEST_PASSWORD, NEW_PASSWORD, "third-sample-passphrase", EMAIL):
        assert secret not in logged
    deliveries = [
        (json.loads(line)["kind"], json.loads(line)["outcome"])
        for line in logged.splitlines()
        if json.loads(line).get("event") == "email_delivery"
    ]
    assert deliveries == [
        ("email_verification", "sent"),  # Phase 7A: sent at signup
        ("password_reset", "sent"),
        ("password_changed", "sent"),  # reset notice
        ("password_changed", "sent"),  # change notice
    ]
