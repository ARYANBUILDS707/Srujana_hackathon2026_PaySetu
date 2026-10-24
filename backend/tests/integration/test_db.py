"""T1.2: engine, SQLite pragmas and session lifecycle."""

from pathlib import Path
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.db as db_module
from app.config import Settings
from app.db import SQLITE_BUSY_TIMEOUT_MS, Database, create_db_engine, get_session, is_sqlite_url
from app.main import create_app


def _pragma(session: Session, name: str) -> Any:
    return session.execute(text(f"PRAGMA {name}")).scalar_one()


def test_sqlite_pragmas_are_applied_on_every_connection(database: Database) -> None:
    with database.session() as session:
        assert str(_pragma(session, "journal_mode")).lower() == "wal"
        assert _pragma(session, "foreign_keys") == 1
        assert _pragma(session, "busy_timeout") == SQLITE_BUSY_TIMEOUT_MS
        assert _pragma(session, "synchronous") == 1  # NORMAL


def test_foreign_keys_are_enforced(database: Database) -> None:
    # Throwaway tables via raw SQL: T1.2 creates no business tables.
    with database.session() as session, session.begin():
        session.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        session.execute(
            text(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES parent(id))"
            )
        )
    with pytest.raises(IntegrityError), database.session() as session, session.begin():
        session.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 999)"))


def test_session_commits_inside_an_explicit_transaction(database: Database) -> None:
    with database.session() as session, session.begin():
        session.execute(text("CREATE TABLE note (body TEXT)"))
        session.execute(text("INSERT INTO note VALUES ('kept')"))
    with database.session() as session:
        assert session.execute(text("SELECT count(*) FROM note")).scalar_one() == 1


def test_session_rolls_back_and_closes_on_error(database: Database) -> None:
    with database.session() as session, session.begin():
        session.execute(text("CREATE TABLE note (body TEXT)"))

    captured: list[Session] = []
    with pytest.raises(RuntimeError, match="boom"), database.session() as session:
        captured.append(session)
        session.execute(text("INSERT INTO note VALUES ('discarded')"))
        raise RuntimeError("boom")

    assert not captured[0].in_transaction()
    with database.session() as session:
        assert session.execute(text("SELECT count(*) FROM note")).scalar_one() == 0


def test_uncommitted_work_is_discarded_when_the_session_closes(database: Database) -> None:
    with database.session() as session, session.begin():
        session.execute(text("CREATE TABLE note (body TEXT)"))
    with database.session() as session:
        session.execute(text("INSERT INTO note VALUES ('never committed')"))
    with database.session() as session:
        assert session.execute(text("SELECT count(*) FROM note")).scalar_one() == 0


def test_sqlite_parent_directory_is_created(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "dir" / "app.db"
    db = Database(f"sqlite:///{db_file}")
    try:
        with db.session() as session:
            session.execute(text("SELECT 1"))
        assert db_file.exists()
    finally:
        db.dispose()


def test_in_memory_sqlite_url_is_supported() -> None:
    db = Database("sqlite://")
    try:
        with db.session() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
            assert _pragma(session, "foreign_keys") == 1
    finally:
        db.dispose()


def test_postgresql_urls_skip_sqlite_options(monkeypatch: pytest.MonkeyPatch) -> None:
    # No PostgreSQL driver is installed (ADR-005 future path); inspect the engine arguments.
    calls: list[dict[str, Any]] = []

    def fake_create_engine(url: Any, **kwargs: Any) -> str:
        calls.append({"url": url, **kwargs})
        return "engine"

    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)
    assert create_db_engine("postgresql+psycopg://user@db.example/paysetu") == "engine"  # type: ignore[comparison-overlap]
    assert calls[0]["pool_pre_ping"] is True and "connect_args" not in calls[0]
    assert not is_sqlite_url("postgresql://user@db.example/paysetu")
    assert is_sqlite_url("sqlite:///./storage/paysetu.db")


def test_get_session_dependency_yields_and_closes_a_session(settings: Settings) -> None:
    app = create_app(settings)
    seen: list[Session] = []

    @app.get("/probe")
    def probe(session: Session = Depends(get_session)) -> dict[str, int]:  # noqa: B008
        seen.append(session)
        return {"one": session.execute(text("SELECT 1")).scalar_one()}

    with TestClient(app) as client:
        assert client.get("/probe").json() == {"one": 1}
    assert not seen[0].in_transaction()
    assert isinstance(app.state.database, Database)


def test_app_disposes_the_engine_on_shutdown(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(settings)
    disposed: list[bool] = []
    original = app.state.database.dispose

    def tracking_dispose() -> None:
        disposed.append(True)
        original()

    monkeypatch.setattr(app.state.database, "dispose", tracking_dispose)
    with TestClient(app):
        assert disposed == []
    assert disposed == [True]
