"""SQLAlchemy models. Import every model module here so Alembic sees the full metadata.

Tables follow DATABASE.md; deviations are listed in each module's docstring.
"""

from app.models.auth import User, UserSession
from app.models.base import Base
from app.models.entities import (
    BankRate,
    Buyer,
    BuyerResponse,
    Case,
    EvidenceItem,
    Supplier,
    TimelineEventRow,
)

__all__ = [
    "BankRate",
    "Base",
    "Buyer",
    "BuyerResponse",
    "Case",
    "EvidenceItem",
    "Supplier",
    "TimelineEventRow",
    "User",
    "UserSession",
]
