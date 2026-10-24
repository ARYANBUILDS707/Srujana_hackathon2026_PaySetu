from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthOut(BaseModel):
    """Liveness response. Phase 1 (T1.7) adds db, storage and adapter modes (API.md 2.1)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
