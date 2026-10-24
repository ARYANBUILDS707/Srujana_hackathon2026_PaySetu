from pathlib import Path

import pytest

from app.config import Settings, load_settings
from app.domain.rules import RuleSet
from app.rules.loader import load_rule_set

# Valid values for every required setting. Placeholder-only test data, never real secrets.
TEST_SETTINGS: dict[str, object] = {
    "app_env": "test",
    "public_base_url": "http://localhost:3000",
    "database_url": "sqlite:///./storage/test.db",
    "storage_dir": "./storage",
    "token_hash_key": "test-only-token-hash-key-0123456789abcdef",
    "email_mode": "simulated",
}


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
    """Valid test settings, ignoring any developer `.env` file."""
    return load_settings(_env_file=None, **{**TEST_SETTINGS, "storage_dir": str(tmp_path)})
