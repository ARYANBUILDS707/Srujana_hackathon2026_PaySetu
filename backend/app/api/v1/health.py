from fastapi import APIRouter

from app.schemas.health import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def get_health() -> HealthOut:
    """Static liveness check (T0.2). Readiness checks are added in T1.7."""
    return HealthOut(status="ok")
