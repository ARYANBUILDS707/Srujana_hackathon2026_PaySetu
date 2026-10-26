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
from sqlalchemy.exc import DatabaseError

from app.models import Base
from tests.conftest import BACKEND_DIR, TEST_SETTINGS, alembic_config

BASELINE = "bf48eb38df15"
DEMO_CORE = "7f9909eb7e4c"  # demo case core (vertical slice)
ACCOUNTS = "099b88746350"  # accounts and ownership (Phase 6)
RESET_TOKENS = "d71bd50903a9"  # password reset tokens (Phase 6.1)
EMAIL_VERIFICATION = "5c2e8a41f0b7"  # email verification (Phase 7A)
ONBOARDING = "8e1f3c9a2b64"  # business onboarding (Phase 7B)
REVIEW = "3d7a9c1e5b20"  # business review (Phase 7C)
HEAD = "6b0d2f4a8c31"  # PostgreSQL append-only triggers and RLS (no-op on SQLite)
DEMO_TABLES = {
    "alembic_version",
    "users",
    "sessions",
    "password_reset_tokens",
    "email_verification_tokens",
    "business_certificates",
    "business_profiles",
    "business_submissions",
    "udyam_claims",
    "reviewer_grants",
    "business_checks",
    "business_check_items",
    "business_reviews",
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
    assert [r.revision for r in script.walk_revisions()] == [
        HEAD,
        REVIEW,
        ONBOARDING,
        EMAIL_VERIFICATION,
        RESET_TOKENS,
        ACCOUNTS,
        DEMO_CORE,
        BASELINE,
    ]


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
        "trg_suppliers_owned_unless_demo_insert",
        "trg_suppliers_owned_unless_demo_update",
        "business_submissions_no_update",
        "business_submissions_no_delete",
        "business_certificates_no_update",
        "business_certificates_no_delete",
        "udyam_claims_no_delete",
        "udyam_claims_contested_only",
        "business_reviews_no_update",
        "business_reviews_no_delete",
        "business_checks_no_update",
        "business_checks_no_delete",
        "business_check_items_no_update",
        "business_check_items_no_delete",
        "reviewer_grants_no_delete",
        "reviewer_grants_revoke_only",
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


# ------------------------------------------------------------ Phase 6: accounts and ownership

_SUPPLIER_INSERT = text(
    "INSERT INTO suppliers (id, legal_name, udyam_verification_status, contact_email, is_demo, "
    "created_at, updated_at) VALUES (:id, 'Sample Supplier (TEST)', 'self_declared', "
    "'s@example.invalid', :is_demo, 't', 't')"
)


def test_existing_demo_data_survives_and_is_not_assigned_to_anyone(
    migrated_database_url: str,
) -> None:
    config = alembic_config(migrated_database_url)
    command.downgrade(config, DEMO_CORE)
    engine = create_engine(migrated_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(_SUPPLIER_INSERT, {"id": "s-demo", "is_demo": True})
            connection.execute(
                text(
                    "INSERT INTO buyers (id, supplier_id, legal_name, created_at, updated_at) "
                    "VALUES ('b-1', 's-demo', 'Sample Buyer (TEST)', 't', 't')"
                )
            )
        command.upgrade(config, HEAD)
        with engine.connect() as connection:
            supplier = connection.execute(
                text("SELECT legal_name, is_demo, owner_user_id FROM suppliers")
            ).one()
            buyers = connection.execute(text("SELECT count(*) FROM buyers")).scalar_one()
            users = connection.execute(text("SELECT count(*) FROM users")).scalar_one()
    finally:
        engine.dispose()
    assert tuple(supplier) == ("Sample Supplier (TEST)", 1, None)
    assert buyers == 1 and users == 0


def test_only_a_demo_supplier_may_be_unowned(migrated_database_url: str) -> None:
    engine = create_engine(migrated_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(_SUPPLIER_INSERT, {"id": "s-demo", "is_demo": True})
        with (
            pytest.raises(DatabaseError, match="only a demo supplier may be unowned"),
            engine.begin() as connection,
        ):
            connection.execute(_SUPPLIER_INSERT, {"id": "s-real", "is_demo": False})
        with (
            pytest.raises(DatabaseError, match="only a demo supplier may be unowned"),
            engine.begin() as connection,
        ):
            connection.execute(text("UPDATE suppliers SET is_demo = 0 WHERE id = 's-demo'"))
    finally:
        engine.dispose()


# ------------------------------------------------------------ Phase 7C: business review

_PROFILE_INSERT = text(
    "INSERT INTO business_profiles (id, supplier_id, status, enterprise_name, "
    "authority_confirmed, revision, status_changed_at, created_at, updated_at) "
    "VALUES (:id, :supplier, :status, 'Sample Enterprise (TEST)', 1, 1, 't', 't', 't')"
)


def test_review_migration_keeps_profiles_and_renames_verified(migrated_database_url: str) -> None:
    config = alembic_config(migrated_database_url)
    command.downgrade(config, ONBOARDING)
    engine = create_engine(migrated_database_url)
    try:
        with engine.begin() as connection:
            for n, status in enumerate(("PENDING_REVIEW", "VERIFIED", "DRAFT")):
                connection.execute(_SUPPLIER_INSERT, {"id": f"s-{n}", "is_demo": True})
                connection.execute(
                    _PROFILE_INSERT, {"id": f"p-{n}", "supplier": f"s-{n}", "status": status}
                )
        command.upgrade(config, HEAD)
        query = text(
            "SELECT id, status, enterprise_name, revision FROM business_profiles ORDER BY id"
        )
        with engine.connect() as connection:
            upgraded = [tuple(row) for row in connection.execute(query)]
            grants = connection.execute(text("SELECT count(*) FROM reviewer_grants")).scalar_one()
        with pytest.raises(DatabaseError), engine.begin() as connection:
            connection.execute(text("UPDATE business_profiles SET status = 'VERIFIED'"))
        command.downgrade(config, ONBOARDING)
        with engine.connect() as connection:
            downgraded = [row[1] for row in connection.execute(query)]
    finally:
        engine.dispose()
    assert upgraded == [
        ("p-0", "PENDING_REVIEW", "Sample Enterprise (TEST)", 1),
        ("p-1", "APPROVED", "Sample Enterprise (TEST)", 1),
        ("p-2", "DRAFT", "Sample Enterprise (TEST)", 1),
    ]
    assert grants == 0  # nobody becomes a reviewer by migration
    assert downgraded == ["PENDING_REVIEW", "VERIFIED", "DRAFT"]
