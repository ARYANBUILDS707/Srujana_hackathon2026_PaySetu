"""Typed errors and `application/problem+json` responses (T1.3; API.md Section 1.4).

Services raise `AppError` subclasses; central handlers turn them, request-validation errors,
HTTP errors and domain validation errors into problem responses. Messages are safe to show
to users: submitted values, stack traces and internal details never appear in responses.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import DomainValidationError

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://paysetu.app/problems/"

_HTTP_CODES: dict[int, tuple[str, str]] = {
    400: ("bad_request", "The request could not be understood"),
    401: ("unauthenticated", "Sign in to continue"),
    403: ("forbidden", "You cannot do this"),
    404: ("not_found", "Not found"),
    405: ("method_not_allowed", "Method not allowed"),
    409: ("conflict", "This conflicts with the current state"),
    413: ("file_too_large", "The upload is too large"),
    415: ("unsupported_file_type", "This file type is not supported"),
    429: ("rate_limited", "Too many requests"),
}


@dataclass(frozen=True)
class FieldError:
    field: str
    code: str
    message: str


class AppError(Exception):
    """Base for errors that map to a problem response. `detail` must be user-safe."""

    status: int = 500
    code: str = "internal_error"
    title: str = "Something went wrong"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        errors: Sequence[FieldError] = (),
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        if code is not None:
            self.code = code
        self.errors = tuple(errors)
        self.headers = headers or {}


class BadRequest(AppError):
    status, code, title = 400, "bad_request", "The request could not be understood"


class Unauthenticated(AppError):
    status, code, title = 401, "unauthenticated", "Sign in to continue"


class Forbidden(AppError):
    status, code, title = 403, "forbidden", "You cannot do this"


class NotFound(AppError):
    status, code, title = 404, "not_found", "Not found"


class Conflict(AppError):
    status, code, title = 409, "conflict", "This conflicts with the current state"


class IntegrityFailed(AppError):
    status, code, title = 409, "integrity_failed", "Integrity check failed"


class PayloadTooLarge(AppError):
    status, code, title = 413, "file_too_large", "The upload is too large"


class UnsupportedFileType(AppError):
    status, code, title = 415, "unsupported_file_type", "This file type is not supported"


class ValidationFailed(AppError):
    status, code, title = 422, "validation_failed", "Some fields need attention"


class RateLimited(AppError):
    status, code, title = 429, "rate_limited", "Too many requests"

    def __init__(self, retry_after_seconds: int, detail: str | None = None) -> None:
        super().__init__(detail, headers={"Retry-After": str(max(1, retry_after_seconds))})


class IntegrationFailed(AppError):
    status, code, title = 502, "integration_failed", "An external service failed"


def problem_response(
    *,
    status: int,
    code: str,
    title: str,
    request_id: str | None,
    detail: str | None = None,
    errors: Sequence[FieldError] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}{code}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail or title,
        "request_id": request_id,
    }
    if errors:
        body["errors"] = [{"field": e.field, "code": e.code, "message": e.message} for e in errors]
    return JSONResponse(body, status_code=status, headers=headers, media_type=PROBLEM_CONTENT_TYPE)


def internal_error_response(request_id: str | None) -> JSONResponse:
    return problem_response(
        status=500,
        code="internal_error",
        title="Something went wrong",
        detail="Something went wrong on our side. Quote the request ID if you contact support.",
        request_id=request_id,
    )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return problem_response(
        status=exc.status,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        errors=exc.errors,
        headers=exc.headers,
        request_id=_request_id(request),
    )


async def _request_validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    issues = exc.errors()
    if any(issue.get("type") == "json_invalid" for issue in issues):
        return problem_response(
            status=400,
            code="bad_request",
            title="The request could not be understood",
            detail="The request body is not valid JSON.",
            request_id=_request_id(request),
        )
    # Only location, type and message: submitted values are never echoed back.
    errors = [
        FieldError(
            field=".".join(str(p) for p in issue.get("loc", ()) if p != "body") or "body",
            code=str(issue.get("type", "invalid")),
            # Custom validators raise ValueError("…"); pydantic prefixes "Value error, ".
            message=str(issue.get("msg", "Invalid value")).removeprefix("Value error, "),
        )
        for issue in issues
    ]
    return problem_response(
        status=422,
        code="validation_failed",
        title="Some fields need attention",
        errors=errors,
        request_id=_request_id(request),
    )


async def _domain_validation(request: Request, exc: Exception) -> JSONResponse:
    # Domain messages describe the rule broken, never internal state (app/domain/errors.py).
    return problem_response(
        status=422,
        code="validation_failed",
        title="Some fields need attention",
        detail=str(exc),
        request_id=_request_id(request),
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, title = _HTTP_CODES.get(exc.status_code, ("http_error", "Request failed"))
    return problem_response(
        status=exc.status_code,
        code=code,
        title=title,
        headers=getattr(exc, "headers", None),
        request_id=_request_id(request),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _request_validation)
    app.add_exception_handler(DomainValidationError, _domain_validation)
    app.add_exception_handler(StarletteHTTPException, _http_error)
