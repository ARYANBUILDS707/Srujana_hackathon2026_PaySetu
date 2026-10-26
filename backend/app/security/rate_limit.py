"""In-memory sliding-window rate limiter with named categories (T1.5; API.md Section 5).

Single-process only (ARCHITECTURE.md 8.5 and 15). Time comes from the injectable `Clock`, so
tests are deterministic. Keys (IP, user, case) live only in memory and are never logged.

The public-share per-IP limit is enforced by `PublicShareRateLimitMiddleware`. Endpoint-
specific categories (login, uploads, sends, packs, ...) are applied by their endpoints, through
`rate_limit_by_ip` or `RateLimiter.hit`, as those endpoints are built.
"""

import math
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.clock import Clock
from app.errors import RateLimited
from app.security._responses import send_problem

SHARE_PREFIX = "/api/v1/public/share/"


class RateLimitCategory(StrEnum):
    LOGIN_ACCOUNT = "login_account"  # POST /auth/login, key IP + email
    LOGIN_IP = "login_ip"  # POST /auth/login, key IP
    SIGNUP = "signup"  # POST /auth/signup, key IP
    PASSWORD_FORGOT = "password_forgot"  # POST /auth/forgot-password, key IP + email
    PASSWORD_FORGOT_IP = "password_forgot_ip"  # POST /auth/forgot-password, key IP
    PASSWORD_RESET = "password_reset"  # POST /auth/reset-password, key IP
    PASSWORD_CHANGE = "password_change"  # POST /auth/change-password, key user
    CERTIFICATE_UPLOAD = "certificate_upload"  # POST /onboarding/certificate, key user
    REVIEW_WRITE = "review_write"  # POST /review/submissions/{id}/checks|decision, key user
    PUBLIC_SHARE = "public_share"  # /public/share/*, key IP
    PUBLIC_SHARE_INVALID_TOKEN = "public_share_invalid_token"  # failed lookups, key IP
    EVIDENCE_UPLOAD = "evidence_upload"  # key user
    COMMUNICATION_SEND = "communication_send"  # key user
    PACK_GENERATION = "pack_generation"  # key case
    INTEGRITY_CHECK = "integrity_check"  # key case
    DEFAULT_USER = "default_user"  # every other supplier route, key user


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


# API.md Section 5.
RATE_LIMITS: dict[RateLimitCategory, RateLimitRule] = {
    RateLimitCategory.LOGIN_ACCOUNT: RateLimitRule(5, 60),
    RateLimitCategory.LOGIN_IP: RateLimitRule(20, 3600),
    RateLimitCategory.SIGNUP: RateLimitRule(5, 3600),
    RateLimitCategory.PASSWORD_FORGOT: RateLimitRule(3, 3600),
    RateLimitCategory.PASSWORD_FORGOT_IP: RateLimitRule(10, 3600),
    RateLimitCategory.PASSWORD_RESET: RateLimitRule(10, 3600),
    RateLimitCategory.PASSWORD_CHANGE: RateLimitRule(5, 900),
    RateLimitCategory.CERTIFICATE_UPLOAD: RateLimitRule(20, 3600),
    RateLimitCategory.REVIEW_WRITE: RateLimitRule(120, 3600),
    RateLimitCategory.PUBLIC_SHARE: RateLimitRule(60, 60),
    RateLimitCategory.PUBLIC_SHARE_INVALID_TOKEN: RateLimitRule(10, 60),
    RateLimitCategory.EVIDENCE_UPLOAD: RateLimitRule(30, 60),
    RateLimitCategory.COMMUNICATION_SEND: RateLimitRule(10, 3600),
    RateLimitCategory.PACK_GENERATION: RateLimitRule(5, 3600),
    RateLimitCategory.INTEGRITY_CHECK: RateLimitRule(10, 3600),
    RateLimitCategory.DEFAULT_USER: RateLimitRule(300, 60),
}


class RateLimiter:
    def __init__(
        self, clock: Clock, rules: dict[RateLimitCategory, RateLimitRule] | None = None
    ) -> None:
        self._clock = clock
        self._rules = dict(RATE_LIMITS if rules is None else rules)
        self._hits: dict[tuple[RateLimitCategory, str], deque[datetime]] = {}
        self._lock = threading.Lock()

    def hit(self, category: RateLimitCategory, key: str) -> None:
        """Record one request; raise `RateLimited` (429 + Retry-After) if over the limit."""
        retry_after = self.check_and_record(category, key)
        if retry_after is not None:
            raise RateLimited(retry_after)

    def check_and_record(self, category: RateLimitCategory, key: str) -> int | None:
        """Record one request and return None, or return seconds to wait if over the limit."""
        rule = self._rules[category]
        now = self._clock.now_utc()
        with self._lock:
            window = self._hits.setdefault((category, key), deque())
            while window and (now - window[0]).total_seconds() >= rule.window_seconds:
                window.popleft()
            if len(window) >= rule.limit:
                elapsed = (now - window[0]).total_seconds()
                return max(1, math.ceil(rule.window_seconds - elapsed))
            window.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(scope: Scope) -> str:
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


def rate_limit_by_ip(category: RateLimitCategory) -> Callable[[Request], None]:
    """FastAPI dependency factory for IP-keyed categories (e.g. signup)."""

    def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        limiter.hit(category, client_ip(request.scope))

    return dependency


class PublicShareRateLimitMiddleware:
    """60 requests / minute per IP on `/api/v1/public/share/*` (API.md Section 5)."""

    def __init__(self, app: ASGIApp, *, limiter: RateLimiter) -> None:
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith(SHARE_PREFIX):
            retry_after = self.limiter.check_and_record(
                RateLimitCategory.PUBLIC_SHARE, client_ip(scope)
            )
            if retry_after is not None:
                await send_problem(
                    scope,
                    receive,
                    send,
                    status=429,
                    code="rate_limited",
                    title="Too many requests",
                    detail="Too many requests. Try again shortly.",
                    headers={"Retry-After": str(retry_after)},
                )
                return
        await self.app(scope, receive, send)
