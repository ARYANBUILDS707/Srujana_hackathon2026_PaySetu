"""Security response headers (T1.5; ARCHITECTURE.md Sections 8.3 and 14).

API responses are JSON or file downloads, so the CSP forbids everything and framing. The
interactive API docs (`/api/v1/docs`) load Swagger UI assets, so they get no CSP. HSTS is sent
only when the public origin is https. Share-token routes also get `no-store`, `no-referrer` and
`noindex`. Headers already set by a handler are not overwritten.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

API_CSP = "default-src 'none'; frame-ancestors 'none'"
HSTS = "max-age=31536000; includeSubDomains"
DOCS_PREFIX = "/api/v1/docs"
SHARE_PREFIX = "/api/v1/public/share/"


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, enable_hsts: bool) -> None:
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope.get("path", "")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self._headers_for(path).items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _headers_for(self, path: str) -> dict[str, str]:
        share = path.startswith(SHARE_PREFIX)
        values = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer" if share else "strict-origin-when-cross-origin",
        }
        if not path.startswith(DOCS_PREFIX):
            values["Content-Security-Policy"] = API_CSP
        if self.enable_hsts:
            values["Strict-Transport-Security"] = HSTS
        if share:
            values["Cache-Control"] = "no-store"
            values["X-Robots-Tag"] = "noindex, nofollow"
        return values
