"""Database engine and sessions (T1.2; ARCHITECTURE.md Section 7; ADR-005).

Nothing here connects at import time. `Database` is built from validated settings when the app
(or a migration) starts; SQLite opens connections lazily on first use.

SQLite connections get the pragmas from ARCHITECTURE.md Section 7 on every connect:
`journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL`.
PostgreSQL (hosted deployment on Supabase) uses the psycopg 3 driver: a plain `postgresql://` or
`postgres://` URL, as Supabase shows it, is mapped to `postgresql+psycopg://`. Server-side
prepared statements are off, so the URL may point at either Supabase pooler mode, and the pool
is kept small for the free tier's connection limit.

Sessions: one per request via `get_session`; services own transactions with
`with session.begin():`. Routers never commit.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

SQLITE_BUSY_TIMEOUT_MS = 5000
POSTGRES_POOL_SIZE = 5
POSTGRES_MAX_OVERFLOW = 5
SQLITE_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}",
    "PRAGMA synchronous=NORMAL",
)


def is_sqlite_url(database_url: str) -> bool:
    return make_url(database_url).get_backend_name() == "sqlite"


def normalise_database_url(database_url: str) -> URL:
    """The URL SQLAlchemy should use: `postgres://` and `postgresql://` mean psycopg 3."""
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url.removeprefix("postgres://")
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def create_db_engine(database_url: str) -> Engine:
    """Create an engine; SQLite files get their parent directory and connection pragmas."""
    url = normalise_database_url(database_url)
    if url.get_backend_name() != "sqlite":
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_size=POSTGRES_POOL_SIZE,
            max_overflow=POSTGRES_MAX_OVERFLOW,
            # Transaction-mode poolers (Supabase port 6543) cannot keep prepared statements.
            connect_args={"prepare_threshold": None},
        )

    if url.database and url.database != ":memory:":
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
    # FastAPI runs sync endpoints in a threadpool; each session still uses one connection.
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        for pragma in SQLITE_PRAGMAS:
            cursor.execute(pragma)
    finally:
        cursor.close()


class Database:
    """Engine plus session factory for one database URL."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_db_engine(database_url)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A session that is always closed; any uncommitted work is rolled back on error."""
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed afterwards."""
    database: Database = request.app.state.database
    with database.session() as session:
        yield session
