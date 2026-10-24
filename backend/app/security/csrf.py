"""CSRF protection for cookie-authenticated API routes (T1.5; API.md 1.2; ARCHITECTURE.md 8.2).

Unsafe methods (POST, PUT, PATCH, DELETE) under `/api/` must carry:
- an `Origin` equal to `PUBLIC_BASE_URL` (or, without Origin, a `Referer` on that origin); and
- the header `X-PaySetu-Client: web` (cross-site forms cannot set custom headers).

`/api/v1/public/*` is exempt: it is token-authenticated and never uses cookies.
Failure returns 403 `csrf_rejected`.
"""

from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

from app.security._responses import send_problem

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CLIENT_HEADER = b"x-paysetu-client"
CLIENT_HEADER_VALUE = b"web"
PROTECTED_PREFIX = "/api/"
EXEMPT_PREFIX = "/api/v1/public/"


class CsrfMiddleware:
    def __init__(self, app: ASGIApp, *, allowed_origin: str) -> None:
        self.app = app
        self.allowed_origin = allowed_origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._requires_check(scope) and not self._passes(scope):
            await send_problem(
                scope,
                receive,
                send,
                status=403,
                code="csrf_rejected",
                title="Request blocked",
                detail="This request was blocked for your security. Reload the page and try again.",
            )
            return
        await self.app(scope, receive, send)

    def _requires_check(self, scope: Scope) -> bool:
        path: str = scope.get("path", "")
        return (
            scope.get("method", "").upper() in UNSAFE_METHODS
            and path.startswith(PROTECTED_PREFIX)
            and not path.startswith(EXEMPT_PREFIX)
        )

    def _passes(self, scope: Scope) -> bool:
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        if headers.get(CLIENT_HEADER) != CLIENT_HEADER_VALUE:
            return False
        origin = headers.get(b"origin")
        if origin is not None:
            return origin.decode("latin-1") == self.allowed_origin
        referer = headers.get(b"referer")
        return referer is not None and _origin_of(referer.decode("latin-1")) == self.allowed_origin


def _origin_of(url: str) -> str | None:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"
