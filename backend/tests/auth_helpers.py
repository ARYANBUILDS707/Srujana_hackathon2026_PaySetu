"""Sign-in helpers for integration tests (Phase 6). Placeholder credentials, never real."""

import re
from email import message_from_bytes, policy
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.clock import Clock
from app.config import Settings
from app.db import Database
from app.schemas.auth import CURRENT_TERMS_VERSION
from app.services.auth import create_demo_account

CSRF = {"Origin": "http://localhost:3000", "X-PaySetu-Client": "web"}
DEMO_EMAIL = "demo@paysetu.example"
TEST_PASSWORD = "sample-test-passphrase-01"  # test-only placeholder


def create_demo_login(settings: Settings, clock: Clock) -> None:
    """Assign the seeded demo supplier to a login, as `make demo-account` does."""
    db = Database(settings.database_url)
    try:
        with db.session() as session:
            # Verified explicitly, like `DEMO_ACCOUNT_VERIFIED=1 make demo-account` (Phase 7A).
            create_demo_account(session, clock, DEMO_EMAIL, TEST_PASSWORD, verified=True)
    finally:
        db.dispose()


def login(client: TestClient, email: str = DEMO_EMAIL, password: str = TEST_PASSWORD) -> Any:
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers=CSRF
    )


def sign_in_as_demo(client: TestClient, settings: Settings, clock: Clock) -> None:
    create_demo_login(settings, clock)
    response = login(client)
    assert response.status_code == 200, response.text


def signup(
    client: TestClient,
    email: str,
    *,
    password: str = TEST_PASSWORD,
    business_name: str = "Sample Traders (TEST)",
    **changes: Any,
) -> Any:
    body = {
        "full_name": "Sample User",
        "business_name": business_name,
        "email": email,
        "password": password,
        "accept_terms_version": CURRENT_TERMS_VERSION,
        **changes,
    }
    return client.post("/api/v1/auth/signup", json=body, headers=CSRF)


VERIFY_LINK = re.compile(r"/verify-email#token=([A-Za-z0-9_-]+)")


def outbox_messages(settings: Settings, email: str, kind: str) -> list[Any]:
    """Messages of `kind` for `email` in the development outbox, oldest first."""
    folder = Path(settings.storage_dir) / "outbox"
    found = []
    for path in sorted(folder.glob("*.eml")) if folder.exists() else []:
        message = message_from_bytes(path.read_bytes(), policy=policy.default)
        if message["To"] == email and message["X-PaySetu-Kind"] == kind:
            found.append(message)
    return found


def latest_verification_token(settings: Settings, email: str) -> str:
    message = outbox_messages(settings, email, "email_verification")[-1]
    match = VERIFY_LINK.search(message.get_content())
    assert match, "verification link not found"
    return match.group(1)


def verify_email(client: TestClient, settings: Settings, email: str) -> None:
    """Complete email verification the way a user does: with the emailed link's token."""
    token = latest_verification_token(settings, email)
    response = client.post("/api/v1/auth/verify-email", json={"token": token}, headers=CSRF)
    assert response.status_code == 200, response.text
