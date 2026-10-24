from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_returns_ok(settings: Settings) -> None:
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_is_served_under_api_prefix(settings: Settings) -> None:
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


def test_app_keeps_the_validated_settings(settings: Settings) -> None:
    assert create_app(settings).state.settings is settings
