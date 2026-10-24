from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import Settings, get_settings

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with `uvicorn app.main:create_app --factory`. Settings are validated before the app is
    built, so a misconfigured server fails at startup with a `ConfigError` (T1.1). Error
    handling, logging and security middleware are added in later Phase 1 tasks.
    """
    resolved = settings if settings is not None else get_settings()
    app = FastAPI(
        title="PaySetu API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.settings = resolved
    app.include_router(api_router, prefix=API_PREFIX)
    return app
