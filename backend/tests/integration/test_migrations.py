"""Alembic configuration, migration history, schema/model parity and repeatability."""

import re
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.models import Base
from tests.conftest import BACKEND_DIR, TEST_SETTINGS, alembic_config

BASELINE = "bf48eb38df15"
HEAD = "7f9909eb7e4c"  # demo case core (vertical slice)
DEMO_TABLES = {
    "alembic_version",
    "suppliers",
    "buyers",
    "cases",
    "evidence_items",
    "timeline_events",
    "buyer_responses",
    "bank_rates",
}


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _version(url: str) -> list[str]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return [
                row[0]
                for row in connection.execute(text("SELECT version_num FROM alembic_version"))
            ]
    finally:
        engine.dispose()


def test_single_linear_history_starting_at_the_baseline() -> None:
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    assert script.get_heads() == [HEAD]
    assert script.get_base() == BASELINE
    assert [r.revision for r in script.walk_revisions()] == [HEAD, BASELINE]


def test_migration_files_follow_the_naming_convention() -> None:
    files = sorted(p.name for p in (BACKEND_DIR / "alembic" / "versions").glob("*.py"))
    assert files, "expected at least the baseline migration"
    assert all(re.fullmatch(r"\d{8}_\d{4}_[a-z0-9_]+\.py", name) for name in files), files


def test_upgrade_head_creates_the_demo_tables(migrated_database_url: str) -> None:
    assert _tables(migrated_database_url) == DEMO_TABLES
    assert _version(migrated_database_url) == [HEAD]


def test_models_match_the_migrated_schema(migrated_database_url: str) -> None:
    # Autogenerate must find nothing to change: migrations and models agree exactly.
    engine = create_engine(migrated_database_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    assert diff == []


def test_append_only_triggers_exist(migrated_database_url: str) -> None:
    engine = create_engine(migrated_database_url)
    try:
        with engine.connect() as connection:
            names = set(
                connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))
                .scalars()
                .all()
            )
    finally:
        engine.dispose()
    assert names == {
        "timeline_events_no_update",
        "timeline_events_no_delete",
        "evidence_items_no_delete",
        "evidence_items_exclusion_only",
    }


def test_baseline_alone_has_only_version_tracking(migrated_database_url: str) -> None:
    command.downgrade(alembic_config(migrated_database_url), BASELINE)
    assert _tables(migrated_database_url) == {"alembic_version"}


def test_downgrade_and_upgrade_are_repeatable(migrated_database_url: str) -> None:
    config = alembic_config(migrated_database_url)
    command.downgrade(config, "base")
    assert _version(migrated_database_url) == []
    command.upgrade(config, "head")
    command.upgrade(config, "head")  # idempotent at head
    assert _version(migrated_database_url) == [HEAD]
    assert _tables(migrated_database_url) == DEMO_TABLES


def test_migrations_run_with_application_pragmas(migrated_database_url: str) -> None:
    # env.py uses app.db.create_db_engine, so the database file is in WAL mode afterwards.
    engine = create_engine(migrated_database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
    finally:
        engine.dispose()


def test_offline_mode_emits_sql_without_a_database(tmp_path: Path) -> None:
    db_file = tmp_path / "never-created.db"
    config = alembic_config(f"sqlite:///{db_file}")
    buffer = StringIO()
    config.output_buffer = buffer
    command.upgrade(config, "head", sql=True)
    assert "alembic_version" in buffer.getvalue()
    assert not db_file.exists()


def test_url_comes_from_validated_settings_when_not_overridden(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    url = f"sqlite:///{tmp_path / 'from-settings.db'}"
    for name, value in {**TEST_SETTINGS, "database_url": url}.items():
        monkeypatch.setenv(name.upper(), str(value))
    monkeypatch.chdir(tmp_path)  # no developer .env
    config = alembic_config("")
    config.attributes.pop("database_url")
    command.upgrade(config, "head")
    assert _version(url) == [HEAD]


def test_invalid_settings_stop_migrations(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.config import ConfigError

    monkeypatch.chdir(tmp_path)
    config = alembic_config("")
    config.attributes.pop("database_url")
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        command.upgrade(config, "head")
