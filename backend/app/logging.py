"""Structured JSON logging and per-request context (T1.3; ARCHITECTURE.md Section 13).

Every request gets a server-generated request ID (never taken from the client), returned in
the `X-Request-ID` header and attached to every log line. One access line is logged per
request with method, redacted path, status and duration. Request/response bodies, query
strings, headers, cookies and tokens are never logged; only allow-listed fields are emitted.
"""

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import internal_error_response

REQUEST_ID_HEADER = "X-Request-ID"
LOGGER_NAME = "paysetu"
_ALLOWED_EXTRA = ("event", "method", "path", "status", "duration_ms", "error_type")
# Share tokens appear in public URLs (API.md Section 7); they are replaced before logging.
_TOKEN_PATH = re.compile(r"^(/api/v1/public/share/)[^/]+")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger(LOGGER_NAME)


def get_request_id() -> str | None:
    return request_id_var.get()


def redact_path(path: str) -> str:
    return _TOKEN_PATH.sub(r"\1{token}", path)


class JsonFormatter(logging.Formatter):
    """One JSON object per line with an allow-list of fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        for key in _ALLOWED_EXTRA:
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    """Send `paysetu.*` logs to stderr as JSON. Safe to call more than once."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


class RequestContextMiddleware:
    """Outermost middleware: request ID, access log, and last-resort 500 problem response.

    It sits outside FastAPI's exception handling, so unexpected exceptions reach it with the
    request ID still known and are answered with a generic `internal_error` problem.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"
                ]
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            logger.exception(
                "Unhandled exception",
                extra={"event": "unhandled_exception", "error_type": type(exc).__name__},
            )
            if response_started:
                raise
            await internal_error_response(request_id)(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request",
                extra={
                    "event": "request",
                    "method": scope.get("method"),
                    "path": redact_path(scope.get("path", "")),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)
