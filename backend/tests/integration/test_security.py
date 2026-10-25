"""T1.5: body size limit, CSRF, security headers and rate limiting."""

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.clock import FrozenClock
from app.config import Settings
from app.errors import PROBLEM_CONTENT_TYPE, RateLimited
from app.main import create_app
from app.security.body_limit import MIB, max_body_bytes
from app.security.headers import API_CSP, HSTS
from app.security.rate_limit import (
    RATE_LIMITS,
    RateLimitCategory,
    RateLimiter,
    RateLimitRule,
    rate_limit_by_ip,
)

ORIGIN = "http://localhost:3000"
CSRF_OK = {"Origin": ORIGIN, "X-PaySetu-Client": "web"}


def _build(settings: Settings, clock: FrozenClock) -> tuple[FastAPI, list[int]]:
    app = create_app(settings, clock=clock)
    body_reads: list[int] = []

    @app.api_route("/api/v1/probe", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def probe(request: Request) -> dict[str, int]:
        body = await request.body()
        body_reads.append(len(body))
        return {"bytes": len(body)}

    @app.post("/api/v1/public/share/{token}/probe")
    def share_post(token: str) -> dict[str, bool]:
        return {"ok": bool(token)}

    @app.get("/api/v1/public/share/{token}")
    def share_get(token: str) -> dict[str, bool]:
        return {"ok": bool(token)}

    @app.get("/api/v1/custom-cache")
    def custom_cache() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"Content-Security-Policy": "custom"})

    @app.post("/probe/outside-api")
    def outside_api() -> dict[str, bool]:
        return {"ok": True}

    @app.post(
        "/api/v1/probe/signup", dependencies=[Depends(rate_limit_by_ip(RateLimitCategory.SIGNUP))]
    )
    def signup_probe() -> dict[str, bool]:
        return {"ok": True}

    return app, body_reads


@pytest.fixture
def small_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"max_upload_mb": 1, "max_case_storage_mb": 1})


@pytest.fixture
def client(small_settings: Settings, frozen_clock: FrozenClock) -> Iterator[TestClient]:
    app, _ = _build(small_settings, frozen_clock)
    with TestClient(app) as test_client:
        yield test_client


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_CONTENT_TYPE
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert body["request_id"] == response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"  # headers on errors too
    return body


# ----------------------------------------------------------------------------- CSRF


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_unsafe_methods_without_csrf_headers_are_rejected(client: TestClient, method: str) -> None:
    _problem(client.request(method, "/api/v1/probe"), 403, "csrf_rejected")


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": ORIGIN},  # missing client header
        {"X-PaySetu-Client": "web"},  # missing Origin and Referer
        {"Origin": ORIGIN, "X-PaySetu-Client": "mobile"},
        {"Origin": "https://evil.example", "X-PaySetu-Client": "web"},
        {"Origin": "http://localhost:3000.evil.example", "X-PaySetu-Client": "web"},
        {"Origin": "null", "X-PaySetu-Client": "web"},
        {"Referer": "https://evil.example/page", "X-PaySetu-Client": "web"},
        {"Referer": "not a url", "X-PaySetu-Client": "web"},
        # Origin takes precedence over a matching Referer.
        {"Origin": "https://evil.example", "Referer": f"{ORIGIN}/app", "X-PaySetu-Client": "web"},
    ],
)
def test_csrf_rejections(client: TestClient, headers: dict[str, str]) -> None:
    body = _problem(client.post("/api/v1/probe", headers=headers), 403, "csrf_rejected")
    assert "blocked" in body["detail"]


@pytest.mark.parametrize(
    "headers", [CSRF_OK, {"Referer": f"{ORIGIN}/app/cases", "X-PaySetu-Client": "web"}]
)
def test_valid_csrf_headers_pass(client: TestClient, headers: dict[str, str]) -> None:
    assert client.post("/api/v1/probe", headers=headers).status_code == 200


def test_safe_methods_public_routes_and_non_api_paths_are_not_checked(client: TestClient) -> None:
    assert client.get("/api/v1/probe").status_code == 200
    assert client.post("/api/v1/public/share/tok/probe").status_code == 200
    assert client.post("/probe/outside-api").status_code == 200


# ----------------------------------------------------------------------- body limit


def test_max_body_bytes_adds_multipart_overhead() -> None:
    assert max_body_bytes(15) == 16 * MIB


def test_declared_oversize_body_is_rejected_before_reading(
    small_settings: Settings, frozen_clock: FrozenClock
) -> None:
    app, body_reads = _build(small_settings, frozen_clock)
    with TestClient(app) as client:
        response = client.post("/api/v1/probe", headers=CSRF_OK, content=b"x" * (2 * MIB + 1))
    _problem(response, 413, "file_too_large")
    assert body_reads == []


def test_streamed_oversize_body_without_length_is_stopped(client: TestClient) -> None:
    chunks = iter([b"x" * MIB] * 3)  # chunked transfer, no Content-Length
    response = client.post("/api/v1/probe", headers=CSRF_OK, content=chunks)
    _problem(response, 413, "file_too_large")


def test_body_at_the_limit_is_accepted(client: TestClient) -> None:
    response = client.post("/api/v1/probe", headers=CSRF_OK, content=b"x" * (2 * MIB))
    assert response.status_code == 200 and response.json() == {"bytes": 2 * MIB}


def test_unparseable_content_length_falls_back_to_counting(client: TestClient) -> None:
    response = client.post(
        "/api/v1/probe",
        headers={**CSRF_OK, "Content-Length": "abc"},
        content=b"small",
    )
    # The bad header is ignored; the streamed bytes are counted and are under the limit.
    assert response.status_code == 200 and response.json() == {"bytes": 5}


def test_csrf_is_checked_before_reading_an_oversize_body(
    small_settings: Settings, frozen_clock: FrozenClock
) -> None:
    app, body_reads = _build(small_settings, frozen_clock)
    with TestClient(app) as client:
        response = client.post("/api/v1/probe", content=b"x" * MIB)
    _problem(response, 403, "csrf_rejected")
    assert body_reads == []


# ------------------------------------------------------------------ security headers


def test_api_responses_carry_security_headers(client: TestClient) -> None:
    headers = client.get("/api/v1/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["content-security-policy"] == API_CSP
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "strict-transport-security" not in headers  # http origin
    assert "x-request-id" in headers


def test_hsts_is_sent_for_https_origins(settings: Settings, frozen_clock: FrozenClock) -> None:
    https = settings.model_copy(update={"public_base_url": "https://paysetu.example"})
    with TestClient(create_app(https, clock=frozen_clock)) as client:
        assert client.get("/api/v1/health").headers["strict-transport-security"] == HSTS


def test_share_routes_are_not_cached_referred_or_indexed(client: TestClient) -> None:
    headers = client.get("/api/v1/public/share/secret-token").headers
    assert headers["cache-control"] == "no-store"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-robots-tag"] == "noindex, nofollow"


def test_docs_page_is_exempt_from_the_api_csp(client: TestClient) -> None:
    response = client.get("/api/v1/docs")
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-frame-options"] == "DENY"


def test_handler_set_headers_are_not_overwritten(client: TestClient) -> None:
    assert client.get("/api/v1/custom-cache").headers["content-security-policy"] == "custom"


def test_error_responses_carry_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/nope")
    _problem(response, 404, "not_found")
    assert response.headers["content-security-policy"] == API_CSP


# --------------------------------------------------------------------- rate limiting


def test_rate_limit_table_matches_api_contract() -> None:
    assert RATE_LIMITS[RateLimitCategory.LOGIN_ACCOUNT] == RateLimitRule(5, 60)
    assert RATE_LIMITS[RateLimitCategory.LOGIN_IP] == RateLimitRule(20, 3600)
    assert RATE_LIMITS[RateLimitCategory.SIGNUP] == RateLimitRule(5, 3600)
    assert RATE_LIMITS[RateLimitCategory.PASSWORD_FORGOT] == RateLimitRule(3, 3600)
    assert RATE_LIMITS[RateLimitCategory.PASSWORD_FORGOT_IP] == RateLimitRule(10, 3600)
    assert RATE_LIMITS[RateLimitCategory.PASSWORD_RESET] == RateLimitRule(10, 3600)
    assert RATE_LIMITS[RateLimitCategory.PASSWORD_CHANGE] == RateLimitRule(5, 900)
    assert RATE_LIMITS[RateLimitCategory.VERIFY_EMAIL] == RateLimitRule(120, 3600)
    assert RATE_LIMITS[RateLimitCategory.VERIFY_RESEND_COOLDOWN] == RateLimitRule(1, 60)
    assert RATE_LIMITS[RateLimitCategory.VERIFY_RESEND] == RateLimitRule(5, 3600)
    assert RATE_LIMITS[RateLimitCategory.CERTIFICATE_UPLOAD] == RateLimitRule(20, 3600)
    assert RATE_LIMITS[RateLimitCategory.PUBLIC_SHARE] == RateLimitRule(60, 60)
    assert RATE_LIMITS[RateLimitCategory.PUBLIC_SHARE_INVALID_TOKEN] == RateLimitRule(10, 60)
    assert RATE_LIMITS[RateLimitCategory.EVIDENCE_UPLOAD] == RateLimitRule(30, 60)
    assert RATE_LIMITS[RateLimitCategory.COMMUNICATION_SEND] == RateLimitRule(10, 3600)
    assert RATE_LIMITS[RateLimitCategory.PACK_GENERATION] == RateLimitRule(5, 3600)
    assert RATE_LIMITS[RateLimitCategory.INTEGRITY_CHECK] == RateLimitRule(10, 3600)
    assert RATE_LIMITS[RateLimitCategory.DEFAULT_USER] == RateLimitRule(300, 60)
    assert set(RATE_LIMITS) == set(RateLimitCategory)


def test_sliding_window_limit_and_retry_after(frozen_clock: FrozenClock) -> None:
    limiter = RateLimiter(frozen_clock)
    category = RateLimitCategory.LOGIN_ACCOUNT  # 5 per 60 s
    for _ in range(5):
        limiter.hit(category, "ip|user@example.in")
        frozen_clock.advance(timedelta(seconds=10))  # hits at t=0,10,20,30,40
    with pytest.raises(RateLimited) as info:
        limiter.hit(category, "ip|user@example.in")  # t=50: oldest frees at t=60
    assert info.value.headers["Retry-After"] == "10"
    frozen_clock.advance(timedelta(seconds=10))  # t=60: the t=0 hit has expired
    limiter.hit(category, "ip|user@example.in")
    with pytest.raises(RateLimited):
        limiter.hit(category, "ip|user@example.in")


def test_keys_and_categories_are_independent(frozen_clock: FrozenClock) -> None:
    limiter = RateLimiter(
        frozen_clock,
        {
            RateLimitCategory.SIGNUP: RateLimitRule(1, 3600),
            RateLimitCategory.LOGIN_IP: RateLimitRule(1, 3600),
        },
    )
    limiter.hit(RateLimitCategory.SIGNUP, "1.1.1.1")
    limiter.hit(RateLimitCategory.SIGNUP, "2.2.2.2")
    limiter.hit(RateLimitCategory.LOGIN_IP, "1.1.1.1")
    assert limiter.check_and_record(RateLimitCategory.SIGNUP, "1.1.1.1") == 3600
    limiter.reset()
    assert limiter.check_and_record(RateLimitCategory.SIGNUP, "1.1.1.1") is None


def test_ip_rate_limit_dependency_returns_429(client: TestClient) -> None:
    for _ in range(5):
        assert client.post("/api/v1/probe/signup", headers=CSRF_OK).status_code == 200
    response = client.post("/api/v1/probe/signup", headers=CSRF_OK)
    _problem(response, 429, "rate_limited")
    assert response.headers["retry-after"] == "3600"


def test_public_share_routes_are_limited_per_ip(
    small_settings: Settings, frozen_clock: FrozenClock
) -> None:
    app, _ = _build(small_settings, frozen_clock)
    with TestClient(app) as client:
        for _ in range(60):
            assert client.get("/api/v1/public/share/tok").status_code == 200
        limited = client.get("/api/v1/public/share/tok")
        _problem(limited, 429, "rate_limited")
        assert limited.headers["retry-after"] == "60"
        assert limited.headers["cache-control"] == "no-store"  # share headers still applied
        assert client.get("/api/v1/health").status_code == 200  # other routes unaffected
        frozen_clock.advance(timedelta(seconds=60))
        assert client.get("/api/v1/public/share/tok").status_code == 200


def test_body_limit_passes_disconnect_messages_through() -> None:
    import asyncio

    from starlette.types import Message, Receive, Scope, Send

    from app.security.body_limit import BodySizeLimitMiddleware

    seen: list[Message] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(await receive())

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        return None

    middleware = BodySizeLimitMiddleware(inner, max_bytes=10)
    scope: Scope = {"type": "http", "method": "POST", "path": "/api/v1/probe", "headers": []}
    asyncio.run(middleware(scope, receive, send))
    assert seen == [{"type": "http.disconnect"}]
