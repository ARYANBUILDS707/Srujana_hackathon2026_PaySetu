"""Phase 6: signup, login, sessions (expiry, sliding, revocation), logout, rate limits."""

import hashlib
import io
import json
import logging
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.clock import FrozenClock, format_utc_timestamp
from app.config import AppEnv, Settings
from app.db import Database
from app.logging import LOGGER_NAME, JsonFormatter
from app.main import create_app
from app.models import Supplier, User, UserSession
from app.schemas.auth import CURRENT_TERMS_VERSION
from app.security import passwords
from app.security.sessions import SESSION_COOKIE
from app.services.auth import create_demo_account
from seed.demo import seed
from tests.auth_helpers import CSRF, TEST_PASSWORD, login, signup

EMAIL = "ravi.sample@example.com"


@pytest.fixture
def auth_settings(settings: Settings, migrated_database_url: str) -> Settings:
    return settings.model_copy(update={"database_url": migrated_database_url})


@pytest.fixture
def client(auth_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    with TestClient(create_app(auth_settings, clock=frozen_clock)) as test_client:
        yield test_client


@pytest.fixture
def db(auth_settings: Settings) -> Iterator[Database]:
    database = Database(auth_settings.database_url)
    try:
        yield database
    finally:
        database.dispose()


def _set_cookie(response: Any) -> str:
    return str(response.headers.get("set-cookie", ""))


def _me(client: TestClient) -> Any:
    return client.get("/api/v1/auth/me")


# ------------------------------------------------------------------------------ signup


def test_signup_creates_user_supplier_and_session(client: TestClient, db: Database) -> None:
    response = signup(client, "  Ravi.Sample@Example.com ")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == EMAIL and body["user"]["full_name"] == "Sample User"
    assert body["supplier"]["legal_name"] == "Sample Traders (TEST)"
    assert body["supplier"]["demo_mode"] is False
    assert response.headers["cache-control"] == "no-store"

    cookie = _set_cookie(response)
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "Secure" not in cookie  # http origin in tests; see the https test below
    token = client.cookies[SESSION_COOKIE]
    assert token not in response.text  # never in a body

    with db.session() as session:
        user = session.scalars(select(User)).one()
        stored = session.scalars(select(UserSession)).one()
        supplier = session.scalars(select(Supplier)).one()
    assert user.password_hash.startswith("$argon2id$") and TEST_PASSWORD not in user.password_hash
    assert user.terms_version == CURRENT_TERMS_VERSION
    assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert stored.ip_hash and stored.ip_hash != "testclient"
    assert supplier.owner_user_id == user.id  # from the session, never from the request

    assert _me(client).json()["user"]["id"] == user.id


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"password": "short-1"}, "password"),
        ({"password": "Password123"}, "password"),  # common, case-insensitively
        ({"password": "x" * 129}, "password"),
        ({"email": "not-an-email"}, "email"),
        ({"accept_terms_version": "2020-01"}, "accept_terms_version"),
        ({"full_name": "   "}, "full_name"),
        ({"business_name": ""}, "business_name"),
    ],
)
def test_signup_validation_names_the_field_and_never_echoes_input(
    client: TestClient, changes: dict[str, str], field: str
) -> None:
    body = dict(changes)
    response = signup(client, body.pop("email", EMAIL), **body)
    assert response.status_code == 422 and response.json()["code"] == "validation_failed"
    assert field in {e["field"] for e in response.json()["errors"]}
    for value in changes.values():
        if value.strip():
            assert value not in response.text
    assert SESSION_COOKIE not in _set_cookie(response)


def test_signup_ignores_no_owner_or_supplier_ids_from_the_client(client: TestClient) -> None:
    response = signup(client, EMAIL, owner_user_id="someone-else", supplier_id="x")
    assert response.status_code == 422  # unknown fields are rejected outright


def test_duplicate_email_is_a_generic_conflict(client: TestClient) -> None:
    assert signup(client, EMAIL).status_code == 201
    again = signup(client, EMAIL.upper(), password="another-sample-passphrase")
    assert again.status_code == 409
    assert again.json()["detail"] == "Could not create an account with these details."


def test_signup_is_rate_limited_per_ip(client: TestClient) -> None:
    for n in range(5):
        assert signup(client, f"user{n}@example.com").status_code == 201
    blocked = signup(client, "user5@example.com")
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0


def test_signup_limit_is_configurable_for_test_runs(
    auth_settings: Settings, frozen_clock: FrozenClock
) -> None:
    relaxed = auth_settings.model_copy(update={"auth_signup_limit_per_hour": 7})
    with TestClient(create_app(relaxed, clock=frozen_clock)) as client:
        codes = [signup(client, f"u{n}@example.com").status_code for n in range(8)]
    assert codes == [201] * 7 + [429]


# ------------------------------------------------------------------------------- login


def test_login_starts_a_new_session(client: TestClient) -> None:
    signup(client, EMAIL)
    first = client.cookies[SESSION_COOKIE]
    client.cookies.clear()
    assert _me(client).status_code == 401

    response = login(client, "RAVI.sample@example.com ")
    assert response.status_code == 200 and response.json()["user"]["email"] == EMAIL
    assert "HttpOnly" in _set_cookie(response)
    assert client.cookies[SESSION_COOKIE] != first
    assert _me(client).status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_answer(client: TestClient) -> None:
    signup(client, EMAIL)
    client.cookies.clear()
    wrong = login(client, EMAIL, "not-the-right-passphrase")
    unknown = login(client, "nobody@example.com", TEST_PASSWORD)
    for response in (wrong, unknown):
        assert response.status_code == 401
        assert response.json()["detail"] == "Email or password is incorrect."
        assert response.json()["code"] == "invalid_credentials"
        assert SESSION_COOKIE not in _set_cookie(response)


def test_inactive_user_cannot_log_in_or_use_a_session(client: TestClient, db: Database) -> None:
    signup(client, EMAIL)
    with db.session() as session, session.begin():
        session.scalars(select(User)).one().is_active = False
    assert _me(client).status_code == 401
    assert login(client).status_code == 401


def test_login_is_rate_limited_per_account_and_ip(client: TestClient) -> None:
    signup(client, EMAIL)
    client.cookies.clear()
    codes = [login(client, EMAIL, "wrong-passphrase-00").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
    # Another account from the same IP is still allowed (until the per-IP hourly limit).
    assert login(client, "other@example.com", "wrong-passphrase-00").status_code == 401


def test_login_per_ip_hourly_limit(client: TestClient) -> None:
    codes = [
        login(client, f"user{n}@example.com", "wrong-passphrase-00").status_code for n in range(21)
    ]
    assert codes == [401] * 20 + [429]


def _login_codes(settings: Settings, clock: FrozenClock, attempts: int) -> list[int]:
    with TestClient(create_app(settings, clock=clock)) as client:
        return [
            login(client, f"user{n}@example.com", "wrong-passphrase-00").status_code
            for n in range(attempts)
        ]


def test_login_ip_limit_is_configurable_for_test_runs(
    auth_settings: Settings, frozen_clock: FrozenClock
) -> None:
    assert auth_settings.app_env is AppEnv.TEST
    relaxed = auth_settings.model_copy(update={"auth_login_ip_limit_per_hour": 22})
    assert _login_codes(relaxed, frozen_clock, 23) == [401] * 22 + [429]


@pytest.mark.parametrize("env", [AppEnv.DEVELOPMENT, AppEnv.PRODUCTION])
def test_a_raised_login_ip_limit_is_not_enforced_outside_test_runs(
    auth_settings: Settings, frozen_clock: FrozenClock, env: AppEnv
) -> None:
    # Built without validation on purpose: the app itself still enforces 20/hour.
    forged = auth_settings.model_copy(update={"app_env": env, "auth_login_ip_limit_per_hour": 500})
    assert _login_codes(forged, frozen_clock, 21) == [401] * 20 + [429]


def test_login_replaces_an_existing_session(client: TestClient) -> None:
    signup(client, EMAIL)
    old = client.cookies[SESSION_COOKIE]
    assert login(client, EMAIL).status_code == 200  # still sending the old cookie
    client.cookies.set(SESSION_COOKIE, old)
    assert _me(client).status_code == 401  # session fixation: the old session was revoked


def test_auth_writes_need_csrf_headers(client: TestClient) -> None:
    body = {"email": EMAIL, "password": TEST_PASSWORD}
    response = client.post("/api/v1/auth/login", json=body)
    assert response.status_code == 403 and response.json()["code"] == "csrf_rejected"
    assert client.post("/api/v1/auth/logout").status_code == 403


def test_passwords_and_tokens_never_reach_the_logs(client: TestClient) -> None:
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        signup(client, EMAIL)
        token = client.cookies[SESSION_COOKIE]
        login(client, EMAIL, "wrong-passphrase-00")
        _me(client)
    finally:
        logger.removeHandler(handler)
    logged = buffer.getvalue()
    assert logged  # requests were logged
    assert TEST_PASSWORD not in logged and "wrong-passphrase-00" not in logged
    assert token not in logged
    for line in logged.splitlines():
        json.loads(line)


# --------------------------------------------------------------------- me and logout


def test_me_requires_a_session_and_is_not_cached(client: TestClient) -> None:
    anonymous = _me(client)
    assert anonymous.status_code == 401 and anonymous.json()["code"] == "unauthenticated"
    assert "set-cookie" not in anonymous.headers  # nothing to clear
    signup(client, EMAIL)
    response = _me(client)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"


def test_logout_revokes_the_session_and_clears_the_cookie(client: TestClient) -> None:
    signup(client, EMAIL)
    token = client.cookies[SESSION_COOKIE]
    response = client.post("/api/v1/auth/logout", headers=CSRF)
    assert response.status_code == 204
    assert f'{SESSION_COOKIE}=""' in _set_cookie(response) or "Max-Age=0" in _set_cookie(response)
    client.cookies.set(SESSION_COOKIE, token)  # replaying the old cookie does not work
    replay = _me(client)
    assert replay.status_code == 401 and replay.json()["code"] == "unauthenticated"
    assert "Max-Age=0" in _set_cookie(replay)  # the stale cookie is cleared


def test_logout_without_a_session_is_harmless(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    client.cookies.set(SESSION_COOKIE, "x" * 500)
    assert client.post("/api/v1/auth/logout", headers=CSRF).status_code == 204


@pytest.mark.parametrize("cookie", ["forged-token", "x" * 129])
def test_forged_or_oversized_cookies_are_rejected(client: TestClient, cookie: str) -> None:
    client.cookies.set(SESSION_COOKIE, cookie)
    response = _me(client)
    assert response.status_code == 401 and "Max-Age=0" in _set_cookie(response)


# ------------------------------------------------------------------------- expiry


def test_idle_session_expires(client: TestClient, frozen_clock: FrozenClock) -> None:
    signup(client, EMAIL)
    frozen_clock.advance(timedelta(hours=167, minutes=59))
    assert _me(client).status_code == 200  # still inside the 7-day idle window
    frozen_clock.advance(timedelta(hours=168))
    response = _me(client)
    assert response.status_code == 401 and response.json()["code"] == "session_expired"
    assert "Max-Age=0" in _set_cookie(response)


def test_activity_slides_the_idle_window_but_not_the_absolute_limit(
    client: TestClient, frozen_clock: FrozenClock
) -> None:
    signup(client, EMAIL)
    for _ in range(29):  # used every day: the idle window keeps sliding
        frozen_clock.advance(timedelta(days=1))
        assert _me(client).status_code == 200
    frozen_clock.advance(timedelta(days=1))  # 30 days after login: absolute expiry
    response = _me(client)
    assert response.status_code == 401 and response.json()["code"] == "session_expired"


def test_last_seen_is_refreshed_at_most_hourly(
    client: TestClient, db: Database, frozen_clock: FrozenClock
) -> None:
    signup(client, EMAIL)

    def last_seen() -> str:
        with db.session() as session:
            return session.scalars(select(UserSession)).one().last_seen_at

    start = last_seen()
    frozen_clock.advance(timedelta(minutes=59))
    _me(client)
    assert last_seen() == start
    frozen_clock.advance(timedelta(minutes=1))
    _me(client)
    assert last_seen() == format_utc_timestamp(frozen_clock.now_utc())


def test_https_origins_get_secure_cookies(
    auth_settings: Settings, frozen_clock: FrozenClock
) -> None:
    secure = auth_settings.model_copy(update={"public_base_url": "https://paysetu.example"})
    headers = {"Origin": "https://paysetu.example", "X-PaySetu-Client": "web"}
    with TestClient(
        create_app(secure, clock=frozen_clock), base_url="https://testserver"
    ) as client:
        body = {
            "full_name": "Sample User",
            "business_name": "Sample Traders (TEST)",
            "email": EMAIL,
            "password": TEST_PASSWORD,
            "accept_terms_version": CURRENT_TERMS_VERSION,
        }
        created = client.post("/api/v1/auth/signup", json=body, headers=headers)
        assert "Secure" in _set_cookie(created) and "HttpOnly" in _set_cookie(created)
        out = client.post("/api/v1/auth/logout", headers=headers)
        assert "Secure" in _set_cookie(out)


def test_auth_routes_are_mounted_in_production(isolated_env: None, tmp_path: Any) -> None:
    production = Settings(
        app_env="production",  # type: ignore[arg-type]
        public_base_url="https://paysetu.example",
        database_url=f"sqlite:///{tmp_path / 'p.db'}",
        storage_dir=tmp_path,
        token_hash_key=SecretStr("production-test-key-0123456789abcdefghijkl"),
        email_mode="smtp",  # type: ignore[arg-type]
        smtp_host="smtp.example",
        email_from="noreply@paysetu.example",
        _env_file=None,  # type: ignore[call-arg]
    )
    with TestClient(create_app(production)) as client:
        assert client.get("/api/v1/auth/me").status_code == 401  # mounted, and protected
        assert client.get("/api/v1/cases").status_code == 404  # evaluation routes are not


# ------------------------------------------------------------------- demo account


def test_demo_account_claims_only_the_unowned_demo_supplier(
    client: TestClient, db: Database, frozen_clock: FrozenClock
) -> None:
    with pytest.raises(ValueError, match="No unowned demo supplier"), db.session() as session:
        create_demo_account(session, frozen_clock, "demo@paysetu.example", TEST_PASSWORD)
    signup(client, EMAIL)  # a real user's supplier is never a candidate
    with db.session() as session:
        seed(session, format_utc_timestamp(frozen_clock.now_utc()))
    with pytest.raises(ValueError, match="DEMO_ACCOUNT_PASSWORD"), db.session() as session:
        create_demo_account(session, frozen_clock, "demo@paysetu.example", "short")
    with pytest.raises(ValueError, match="not a valid email"), db.session() as session:
        create_demo_account(session, frozen_clock, "not-an-email", TEST_PASSWORD)
    with pytest.raises(ValueError, match="already exists"), db.session() as session:
        create_demo_account(session, frozen_clock, EMAIL, TEST_PASSWORD)
    with db.session() as session:
        user_id = create_demo_account(session, frozen_clock, "Demo@PaySetu.example", TEST_PASSWORD)
    with db.session() as session:
        suppliers = {s.legal_name: s.owner_user_id for s in session.scalars(select(Supplier))}
    assert suppliers["Ravi Fasteners (DEMO - synthetic data)"] == user_id
    assert suppliers["Sample Traders (TEST)"] != user_id
    with (
        pytest.raises(ValueError, match="No unowned demo supplier"),
        db.session() as session,
    ):  # never claimed twice
        create_demo_account(session, frozen_clock, "second@example.com", TEST_PASSWORD)
    client.cookies.clear()
    me = login(client, "demo@paysetu.example").json()
    assert me["supplier"]["demo_mode"] is True


# ------------------------------------------------------------------- password helpers


def test_password_helpers() -> None:
    hashed = passwords.hash_password(TEST_PASSWORD)
    assert passwords.verify_password(hashed, TEST_PASSWORD)
    assert not passwords.verify_password(hashed, "something-else-entirely")
    assert not passwords.verify_password(None, TEST_PASSWORD)  # unknown account
    assert not passwords.verify_password("not-a-hash", TEST_PASSWORD)
    assert not passwords.needs_rehash(hashed)
    assert passwords.password_problem("0123456789") is not None
    assert passwords.password_problem(TEST_PASSWORD) is None


def test_concurrent_duplicate_signup_is_a_generic_conflict(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate losing the race: the duplicate check sees nothing, the unique index refuses.
    assert signup(client, EMAIL).status_code == 201
    calls: list[int] = []

    def blind_first_lookup(*args: Any) -> Any:
        query = select(*args)
        calls.append(1)
        return query.where(User.id == "no-such-user") if len(calls) == 1 else query

    monkeypatch.setattr("app.services.auth.select", blind_first_lookup)
    again = signup(client, EMAIL, password="another-sample-passphrase")
    assert again.status_code == 409
    assert again.json()["detail"] == "Could not create an account with these details."


def test_a_user_without_a_supplier_cannot_sign_in(client: TestClient, db: Database) -> None:
    signup(client, EMAIL)
    client.cookies.clear()
    with db.session() as session, session.begin():
        supplier = session.scalars(select(Supplier)).one()
        supplier.owner_user_id = None
        supplier.is_demo = True  # the only way a supplier may be unowned
    response = login(client, EMAIL)
    assert response.status_code == 401 and response.json()["code"] == "invalid_credentials"
