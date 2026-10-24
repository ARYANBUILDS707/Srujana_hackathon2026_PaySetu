from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.config import Settings, load_settings
from app.db import Database
from app.domain.rules import RuleSet
from app.rules.loader import load_rule_set

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Valid values for every required setting. Placeholder-only test data, never real secrets.
TEST_SETTINGS: dict[str, object] = {
    "app_env": "test",
    "public_base_url": "http://localhost:3000",
    "database_url": "sqlite:///./storage/test.db",
    "storage_dir": "./storage",
    "token_hash_key": "test-only-token-hash-key-0123456789abcdef",
    "email_mode": "simulated",
}


def alembic_config(database_url: str) -> Config:
    """Alembic config for the project migrations, pointed at an explicit database URL."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture(scope="session")
def rule_set() -> RuleSet:
    return load_rule_set("msmed-v1")


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove PaySetu variables from the process environment for the test."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings(isolated_env: None, tmp_path: Path) -> Settings:
    """Valid test settings, ignoring any developer `.env` file; storage and DB in tmp_path."""
    return load_settings(
        _env_file=None,
        **{
            **TEST_SETTINGS,
            "storage_dir": str(tmp_path),
            "database_url": f"sqlite:///{tmp_path / 'app.db'}",
        },
    )


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> str:
    """A fresh SQLite file per test, built with `alembic upgrade head` (DATABASE.md 8)."""
    url = f"sqlite:///{tmp_path / 'paysetu-test.db'}"
    command.upgrade(alembic_config(url), "head")
    return url


@pytest.fixture
def database(migrated_database_url: str) -> Iterator[Database]:
    db = Database(migrated_database_url)
    try:
        yield db
    finally:
        db.dispose()
