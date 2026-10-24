from fastapi import FastAPI

from app.api.v1 import api_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build the FastAPI application.

    Settings, error handling, logging and security middleware are added in Phase 1.
    """
    app = FastAPI(
        title="PaySetu API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
