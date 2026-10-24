"""baseline

Revision ID: bf48eb38df15
Revises:
Create Date: 2026-10-24 22:48:24.522585+00:00

Empty baseline (T1.2). It establishes Alembic version tracking before any business table
exists. The first schema migration (users, sessions) chains from this revision in Phase 3,
following the order in DATABASE.md Section 8.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "bf48eb38df15"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
