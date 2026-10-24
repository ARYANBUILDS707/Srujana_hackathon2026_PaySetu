"""T1.1: typed settings, startup validation and the production gate."""

from pathlib import Path
from typing import Any

import pytest

from app.config import (
    AppEnv,
    ConfigError,
    EmailMode,
    Settings,
    VerificationMode,
    get_settings,
    load_settings,
)
from app.main import create_app
from tests.conftest import TEST_SETTINGS

SECRET = "super-secret-value-that-must-never-be-logged-0123456789"


def _load(**changes: Any) -> Settings:
    values = {**TEST_SETTINGS, **changes}
    return load_settings(_env_file=None, **{k: v for k, v in values.items() if v is not None})


def _error(**changes: Any) -> str:
    with pytest.raises(ConfigError) as info:
        _load(**changes)
    return str(info.value)


PRODUCTION_LIVE: dict[str, Any] = {
    "app_env": "production",
    "public_base_url": "https://paysetu.example",
    "token_hash_key": SECRET,
    "email_mode": "smtp",
    "smtp_host": "smtp.example",
    "email_from": "noreply@paysetu.example",
}


# ----------------------------------------------------------------------- loading


def test_valid_minimal_settings_apply_documented_defaults(isolated_env: None) -> None:
    s = _load()
    assert s.app_env is AppEnv.TEST and s.email_mode is EmailMode.SIMULATED
    assert (s.session_idle_hours, s.session_absolute_days) == (168, 30)
    assert (s.max_upload_mb, s.max_case_storage_mb) == (15, 200)
    assert s.verification_mode is VerificationMode.OFF
    assert s.smtp_port == 587 and s.smtp_starttls is True
    assert s.allow_nonlive_verified is False and s.log_level == "INFO"
    assert isinstance(s.storage_dir, Path)


def test_settings_are_read_from_environment_variables(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {
        **TEST_SETTINGS,
        "ALLOW_NONLIVE_VERIFIED": "1",
        "MAX_UPLOAD_MB": "10",
    }.items():
        monkeypatch.setenv(name.upper(), str(value))
    s = load_settings(_env_file=None)
    assert s.allow_nonlive_verified is True and s.max_upload_mb == 10


def test_settings_are_read_from_an_env_file(isolated_env: None, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(f"{k.upper()}={v}" for k, v in TEST_SETTINGS.items()) + "\nSMTP_HOST=\n",
        encoding="utf-8",
    )
    s = load_settings(_env_file=env_file)
    assert s.smtp_host is None  # blank optional values become None


def test_the_example_env_file_is_valid_for_development(isolated_env: None) -> None:
    example = Path(__file__).resolve().parents[2] / ".env.example"
    s = load_settings(_env_file=example)
    assert s.app_env is AppEnv.DEVELOPMENT and s.show_simulated_banner


def test_settings_are_immutable(isolated_env: None) -> None:
    s = _load()
    with pytest.raises(ValueError):
        s.app_env = AppEnv.PRODUCTION


def test_secrets_are_hidden_in_repr(isolated_env: None) -> None:
    s = _load(token_hash_key=SECRET, smtp_password=SECRET, smtp_username="u")
    assert SECRET not in repr(s) and SECRET not in str(s)


# -------------------------------------------------------------- validation errors


def test_missing_required_variables_are_named_in_one_message(isolated_env: None) -> None:
    with pytest.raises(ConfigError) as info:
        load_settings(_env_file=None)
    message = str(info.value)
    for name in (
        "APP_ENV",
        "PUBLIC_BASE_URL",
        "DATABASE_URL",
        "STORAGE_DIR",
        "TOKEN_HASH_KEY",
        "EMAIL_MODE",
    ):
        assert name in message


def test_error_messages_never_contain_submitted_values(isolated_env: None) -> None:
    short_secret = "short-secret-xyz"
    message = _error(token_hash_key=short_secret)
    assert "TOKEN_HASH_KEY" in message and "at least 32 bytes" in message
    assert short_secret not in message


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"app_env": "staging"}, "APP_ENV"),
        ({"email_mode": "carrier-pigeon"}, "EMAIL_MODE"),
        ({"verification_mode": "live"}, "VERIFICATION_MODE"),
        ({"log_level": "TRACE"}, "LOG_LEVEL"),
        ({"public_base_url": "ftp://paysetu.example"}, "http(s) origin"),
        ({"public_base_url": "localhost:3000"}, "http(s) origin"),
        ({"public_base_url": "https://paysetu.example/app"}, "origin only"),
        ({"public_base_url": "https://paysetu.example?x=1"}, "origin only"),
        ({"database_url": "mysql://db"}, "sqlite:// or postgresql"),
        ({"session_idle_hours": 0}, "SESSION_IDLE_HOURS"),
        ({"max_upload_mb": 0}, "MAX_UPLOAD_MB"),
        ({"smtp_port": 70000}, "SMTP_PORT"),
        ({"max_upload_mb": 50, "max_case_storage_mb": 40}, "MAX_CASE_STORAGE_MB must be at least"),
        ({"email_mode": "smtp"}, "requires SMTP_HOST and EMAIL_FROM"),
        (
            {"email_mode": "smtp", "smtp_host": "h", "email_from": "a@b.c", "smtp_username": "u"},
            "set together",
        ),
        ({"verification_mode": "sandbox"}, "requires CASHFREE_CLIENT_ID"),
    ],
)
def test_invalid_values_are_rejected(
    isolated_env: None, changes: dict[str, Any], fragment: str
) -> None:
    assert fragment in _error(**changes)


def test_public_base_url_is_normalised_to_an_origin(isolated_env: None) -> None:
    assert (
        _load(public_base_url="https://paysetu.example/").public_base_url
        == "https://paysetu.example"
    )


def test_postgresql_url_is_accepted(isolated_env: None) -> None:
    assert _load(database_url="postgresql+psycopg://u@h/db").database_url.startswith("postgresql")


def test_complete_smtp_and_sandbox_configuration_is_valid(isolated_env: None) -> None:
    s = _load(
        email_mode="smtp",
        smtp_host="smtp.example",
        email_from="noreply@paysetu.example",
        smtp_username="user",
        smtp_password=SECRET,
        verification_mode="sandbox",
        cashfree_client_id="id",
        cashfree_client_secret=SECRET,
        cashfree_base_url="https://sandbox.example",
    )
    assert s.nonlive_adapters == ("verification=sandbox",)


# --------------------------------------------------------------- production gate


def test_production_with_live_adapters_starts(isolated_env: None) -> None:
    s = _load(**PRODUCTION_LIVE)
    assert s.nonlive_adapters == () and not s.show_simulated_banner


@pytest.mark.parametrize(
    ("changes", "adapter"),
    [
        ({"email_mode": "simulated"}, "email=simulated"),
        ({"verification_mode": "simulated"}, "verification=simulated"),
        (
            {
                "verification_mode": "sandbox",
                "cashfree_client_id": "id",
                "cashfree_client_secret": SECRET,
                "cashfree_base_url": "https://sandbox.example",
            },
            "verification=sandbox",
        ),
    ],
)
def test_production_gate_blocks_nonlive_adapters(
    isolated_env: None, changes: dict[str, Any], adapter: str
) -> None:
    message = _error(**{**PRODUCTION_LIVE, **changes})
    assert "non-live adapters in production" in message and adapter in message


def test_production_override_allows_nonlive_adapters_with_banner(isolated_env: None) -> None:
    s = _load(**{**PRODUCTION_LIVE, "email_mode": "simulated", "allow_nonlive_verified": True})
    assert s.show_simulated_banner and s.nonlive_adapters == ("email=simulated",)


def test_production_requires_https(isolated_env: None) -> None:
    assert "https in production" in _error(
        **{**PRODUCTION_LIVE, "public_base_url": "http://x.example"}
    )


def test_production_rejects_the_example_token_key(isolated_env: None) -> None:
    message = _error(**{**PRODUCTION_LIVE, "token_hash_key": "replace-with-32-plus-random-bytes"})
    assert "example value" in message


def test_development_allows_simulated_adapters_without_override(isolated_env: None) -> None:
    s = _load(app_env="development", verification_mode="simulated")
    assert s.show_simulated_banner


# ------------------------------------------------------------------ app startup


def test_app_startup_fails_clearly_without_configuration(
    isolated_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)  # no .env here
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigError, match="Invalid PaySetu configuration"):
            create_app()
    finally:
        get_settings.cache_clear()


def test_get_settings_loads_once(isolated_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in TEST_SETTINGS.items():
        monkeypatch.setenv(name.upper(), str(value))
    monkeypatch.chdir(Path(__file__).parent)  # avoid any developer .env
    get_settings.cache_clear()
    try:
        assert get_settings() is get_settings()
        assert create_app().state.settings is get_settings()
    finally:
        get_settings.cache_clear()
