from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import Settings, get_settings
from app.db import Database

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with `uvicorn app.main:create_app --factory`. Settings are validated before the app is
    built, so a misconfigured server fails at startup with a `ConfigError` (T1.1). The database
    engine is created here, never at import time, and disposed of on shutdown (T1.2). Error
    handling, logging and security middleware are added in later Phase 1 tasks.
    """
    resolved = settings if settings is not None else get_settings()
    database = Database(resolved.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(
        title="PaySetu API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.database = database
    app.include_router(api_router, prefix=API_PREFIX)
    return app
