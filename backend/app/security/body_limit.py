"""Request body size limit (T1.5; ARCHITECTURE.md Section 3.3).

The cap is `MAX_UPLOAD_MB` plus 1 MiB for multipart framing. A declared `Content-Length` over
the cap is rejected before the body is read; bodies without one (chunked) are counted as they
stream and stopped as soon as they exceed it.
"""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.security._responses import send_problem

MIB = 1024 * 1024
MULTIPART_OVERHEAD_BYTES = MIB
_TOO_LARGE = "The request is too large."


def max_body_bytes(max_upload_mb: int) -> int:
    return max_upload_mb * MIB + MULTIPART_OVERHEAD_BYTES


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _content_length(scope)
        if declared is not None and declared > self.max_bytes:
            await send_problem(
                scope,
                receive,
                send,
                status=413,
                code="file_too_large",
                title="The upload is too large",
                detail=_TOO_LARGE,
            )
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # Starlette HTTPExceptions pass through FastAPI's body parsing unchanged and
                    # become a 413 problem response via the T1.3 handlers.
                    raise HTTPException(status_code=413, detail=_TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
