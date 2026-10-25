"""Sign-in helpers for integration tests (Phase 6). Placeholder credentials, never real."""

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
            create_demo_account(session, clock, DEMO_EMAIL, TEST_PASSWORD)
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
