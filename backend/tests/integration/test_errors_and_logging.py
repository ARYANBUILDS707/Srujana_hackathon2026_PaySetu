"""T1.3: problem+json errors, request IDs and safe structured logging."""

import json
import logging
import re
from collections.abc import Iterator
from io import StringIO
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import Settings
from app.domain.errors import DomainValidationError
from app.errors import (
    PROBLEM_CONTENT_TYPE,
    Conflict,
    FieldError,
    IntegrationFailed,
    NotFound,
    RateLimited,
    ValidationFailed,
)
from app.logging import LOGGER_NAME, JsonFormatter, configure_logging, redact_path
from app.main import create_app

SECRET = "super-secret-token-value-do-not-log"
REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")


class Payload(BaseModel):
    amount: int
    note: str


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    application = create_app(settings)

    @application.get("/probe/not-found")
    def not_found() -> None:
        raise NotFound("Case not found or you don't have access.")

    @application.get("/probe/conflict")
    def conflict() -> None:
        raise Conflict("Already sent.", code="already_sent")

    @application.get("/probe/validation")
    def validation() -> None:
        raise ValidationFailed(
            errors=[FieldError("delivery_date", "date_in_future", "Cannot be in the future.")]
        )

    @application.get("/probe/rate-limited")
    def rate_limited() -> None:
        raise RateLimited(retry_after_seconds=30)

    @application.get("/probe/integration")
    def integration() -> None:
        raise IntegrationFailed("Email could not be sent. Your letter is saved.")

    @application.get("/probe/domain")
    def domain() -> None:
        raise DomainValidationError("Delivery date cannot be in the future.")

    @application.get("/probe/crash")
    def crash() -> None:
        raise RuntimeError(f"database password={SECRET}")

    @application.post("/probe/body")
    def body(payload: Payload) -> dict[str, int]:
        return {"amount": payload.amount}

    @application.get("/api/v1/public/share/{token}")
    def share(token: str) -> dict[str, bool]:
        return {"ok": bool(token)}

    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_CONTENT_TYPE
    body: dict[str, Any] = response.json()
    assert body["status"] == status and body["code"] == code
    assert body["type"] == f"https://paysetu.app/problems/{code}"
    assert body["title"] and body["detail"]
    assert body["request_id"] == response.headers["x-request-id"]
    return body


# ------------------------------------------------------------------ problem responses


@pytest.mark.parametrize(
    ("path", "status", "code", "detail"),
    [
        ("/probe/not-found", 404, "not_found", "Case not found or you don't have access."),
        ("/probe/conflict", 409, "already_sent", "Already sent."),
        (
            "/probe/integration",
            502,
            "integration_failed",
            "Email could not be sent. Your letter is saved.",
        ),
        ("/probe/domain", 422, "validation_failed", "Delivery date cannot be in the future."),
    ],
)
def test_app_errors_become_problem_responses(
    client: TestClient, path: str, status: int, code: str, detail: str
) -> None:
    assert _assert_problem(client.get(path), status, code)["detail"] == detail


def test_validation_failed_lists_field_errors(client: TestClient) -> None:
    body = _assert_problem(client.get("/probe/validation"), 422, "validation_failed")
    assert body["errors"] == [
        {"field": "delivery_date", "code": "date_in_future", "message": "Cannot be in the future."}
    ]


def test_rate_limited_sets_retry_after(client: TestClient) -> None:
    response = client.get("/probe/rate-limited")
    _assert_problem(response, 429, "rate_limited")
    assert response.headers["retry-after"] == "30"


def test_request_validation_errors_do_not_echo_submitted_values(client: TestClient) -> None:
    response = client.post("/probe/body", json={"amount": SECRET})
    body = _assert_problem(response, 422, "validation_failed")
    fields = {e["field"]: e for e in body["errors"]}
    assert set(fields) == {"amount", "note"}
    assert fields["note"]["code"] == "missing"
    assert SECRET not in response.text


def test_malformed_json_is_a_bad_request(client: TestClient) -> None:
    response = client.post(
        "/probe/body", content=b'{"amount": 1,', headers={"content-type": "application/json"}
    )
    assert (
        _assert_problem(response, 400, "bad_request")["detail"]
        == "The request body is not valid JSON."
    )


def test_unknown_route_and_wrong_method_are_problems(client: TestClient) -> None:
    _assert_problem(client.get("/api/v1/does-not-exist"), 404, "not_found")
    _assert_problem(client.post("/api/v1/health"), 405, "method_not_allowed")


def test_unexpected_exception_is_generic_and_leaks_nothing(client: TestClient) -> None:
    response = client.get("/probe/crash")
    body = _assert_problem(response, 500, "internal_error")
    assert SECRET not in response.text and "RuntimeError" not in response.text
    assert "request ID" in body["detail"]


def test_crash_is_logged_server_side_with_the_request_id(app: FastAPI) -> None:
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/probe/crash")
    finally:
        logger.removeHandler(handler)
    entries = [json.loads(line) for line in buffer.getvalue().splitlines()]
    crash = next(e for e in entries if e.get("event") == "unhandled_exception")
    assert crash["request_id"] == response.headers["x-request-id"]
    assert crash["error_type"] == "RuntimeError" and "Traceback" in crash["exception"]
    access = next(e for e in entries if e.get("event") == "request")
    assert access["status"] == 500


# ------------------------------------------------------------------- request IDs


def test_every_response_has_a_unique_request_id(client: TestClient) -> None:
    first, second = client.get("/api/v1/health"), client.get("/api/v1/health")
    for response in (first, second):
        assert REQUEST_ID.fullmatch(response.headers["x-request-id"])
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_client_supplied_request_id_is_ignored(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "attacker\ninjected"})
    assert REQUEST_ID.fullmatch(response.headers["x-request-id"])
    assert response.headers.get_list("x-request-id") == [response.headers["x-request-id"]]


def test_health_endpoint_is_unchanged(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


# ----------------------------------------------------------------------- logging


def test_access_log_is_structured_and_safe(app: FastAPI) -> None:
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/probe/body?api_key={SECRET}",
                json={"amount": 5, "note": SECRET},
                headers={"Authorization": f"Bearer {SECRET}", "Cookie": f"ps_session={SECRET}"},
            )
            share = client.get(f"/api/v1/public/share/{SECRET}")
    finally:
        logger.removeHandler(handler)

    raw = buffer.getvalue()
    assert SECRET not in raw  # no body, query string, header, cookie or token
    entries = [json.loads(line) for line in raw.splitlines()]
    body_line, share_line = [e for e in entries if e.get("event") == "request"]
    assert body_line["method"] == "POST" and body_line["path"] == "/probe/body"
    assert body_line["status"] == 200 and body_line["duration_ms"] >= 0
    assert body_line["request_id"] == response.headers["x-request-id"]
    assert body_line["level"] == "INFO" and body_line["timestamp"].endswith("+00:00")
    assert share_line["path"] == "/api/v1/public/share/{token}"
    assert share.status_code == 200


def test_formatter_drops_unknown_extra_fields() -> None:
    record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 1, "hello", None, None)
    record.password = SECRET
    record.status = 201
    entry = json.loads(JsonFormatter().format(record))
    assert SECRET not in json.dumps(entry)
    assert entry["status"] == 201 and entry["message"] == "hello"
    assert entry["request_id"] is None


def test_configure_logging_is_idempotent() -> None:
    configure_logging("WARNING")
    configure_logging("INFO")
    logger = logging.getLogger(LOGGER_NAME)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)
    assert logger.level == logging.INFO and logger.propagate is False


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/public/share/abc123", "/api/v1/public/share/{token}"),
        ("/api/v1/public/share/abc123/pack", "/api/v1/public/share/{token}/pack"),
        ("/api/v1/cases/42", "/api/v1/cases/42"),
    ],
)
def test_redact_path(path: str, expected: str) -> None:
    assert redact_path(path) == expected


def test_crash_after_streaming_started_is_logged_and_reraised(settings: Settings) -> None:
    from fastapi.responses import StreamingResponse

    application = create_app(settings)

    def broken_stream() -> Iterator[bytes]:
        yield b"partial"
        raise RuntimeError("stream failed")

    @application.get("/probe/stream")
    def stream() -> StreamingResponse:
        return StreamingResponse(broken_stream())

    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        # Headers were already sent, so no problem response can replace them.
        with TestClient(application) as client, pytest.raises(RuntimeError, match="stream failed"):
            client.get("/probe/stream")
    finally:
        logger.removeHandler(handler)
    events = [json.loads(line).get("event") for line in buffer.getvalue().splitlines()]
    assert "unhandled_exception" in events and "request" in events
