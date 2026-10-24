from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.clock import Clock, SystemClock
from app.config import Settings, get_settings
from app.db import Database
from app.errors import register_error_handlers
from app.logging import RequestContextMiddleware, configure_logging

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    """Build the FastAPI application.

    Run with `uvicorn app.main:create_app --factory`. Settings are validated before the app is
    built, so a misconfigured server fails at startup with a `ConfigError` (T1.1). The database
    engine is created here, never at import time, and disposed of on shutdown (T1.2). Errors
    become `application/problem+json` responses with a request ID, and logs are JSON (T1.3).
    Security middleware is added in T1.5.
    """
    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)
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
    # Injectable time source (T1.4): tests pass a FrozenClock.
    app.state.clock = clock if clock is not None else SystemClock()
    app.include_router(api_router, prefix=API_PREFIX)
    register_error_handlers(app)
    # Added last, so it is the outermost middleware: it wraps every response and error.
    app.add_middleware(RequestContextMiddleware)
    return app
