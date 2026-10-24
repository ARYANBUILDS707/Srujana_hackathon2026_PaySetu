"""SQLAlchemy models. Import every model module here so Alembic sees the full metadata.

No business tables exist yet (T1.2 creates only the migration baseline); they are added by the
migrations listed in DATABASE.md Section 8, starting with Phase 3.
"""

from app.models.base import Base

__all__ = ["Base"]
