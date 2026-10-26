"""Typed application settings (T1.1; ARCHITECTURE.md Sections 10 and 12).

Configuration comes only from environment variables, optionally via `backend/.env`.
`load_settings` turns validation failures into a `ConfigError` that names each problem
variable and the reason, never the submitted value, so secrets cannot leak into logs.

Production gate (ARCHITECTURE.md Section 10): with `APP_ENV=production`, startup fails if
any adapter is not live (`EMAIL_MODE=simulated`, or `VERIFICATION_MODE` simulated/sandbox),
unless `ALLOW_NONLIVE_VERIFIED=1`. Sandbox counts as non-live because its results are not
real registry checks. Whenever an adapter is non-live, the UI shows the simulated banner.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_TOKEN_HASH_KEY_BYTES = 32
DEFAULT_SIGNUP_LIMIT_PER_HOUR = 5
DEFAULT_LOGIN_IP_LIMIT_PER_HOUR = 20  # API.md Section 5: POST /auth/login, 20/hour per IP
_EXAMPLE_TOKEN_HASH_KEY = "replace-with-32-plus-random-bytes"
_DATABASE_SCHEMES = ("sqlite://", "postgresql://", "postgresql+")


class ConfigError(RuntimeError):
    """Settings are missing or invalid. The message is safe to log."""


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class EmailMode(StrEnum):
    SMTP = "smtp"
    SIMULATED = "simulated"


class VerificationMode(StrEnum):
    OFF = "off"
    SIMULATED = "simulated"
    SANDBOX = "sandbox"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    app_env: AppEnv
    public_base_url: str
    database_url: str
    storage_dir: Path
    token_hash_key: SecretStr

    session_idle_hours: int = Field(default=168, ge=1, le=24 * 90)
    session_absolute_days: int = Field(default=30, ge=1, le=365)
    # Signups per hour per IP (API.md Section 5: 5). Raised only for automated test runs that
    # create many accounts from one address; production refuses anything above the default.
    # Phase 7B: largest accepted Udyam certificate PDF.
    business_certificate_max_mb: int = Field(default=5, ge=1, le=15)
    auth_signup_limit_per_hour: int = Field(default=DEFAULT_SIGNUP_LIMIT_PER_HOUR, ge=1, le=1000)
    # Logins per hour per IP (Phase 7D). A higher value is accepted only with APP_ENV=test
    # (automated runs that sign in many accounts from 127.0.0.1); development and production
    # refuse it at startup. The per-account limit (5/min per IP + email) is not configurable.
    auth_login_ip_limit_per_hour: int = Field(
        default=DEFAULT_LOGIN_IP_LIMIT_PER_HOUR, ge=1, le=1000
    )
    max_upload_mb: int = Field(default=15, ge=1, le=100)
    max_case_storage_mb: int = Field(default=200, ge=1, le=10_000)

    email_mode: EmailMode
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    email_from: str | None = None

    verification_mode: VerificationMode = VerificationMode.OFF
    cashfree_client_id: str | None = None
    cashfree_client_secret: SecretStr | None = None
    cashfree_base_url: str | None = None

    allow_nonlive_verified: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator(
        "smtp_host",
        "smtp_username",
        "email_from",
        "cashfree_client_id",
        "cashfree_base_url",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        # `.env.example` lists optional variables with empty values.
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("smtp_password", "cashfree_client_secret", mode="before")
    @classmethod
    def _blank_secret_to_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("public_base_url")
    @classmethod
    def _check_origin(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("must be an http(s) origin such as https://paysetu.example")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError("must be an origin only (no path, query or fragment)")
        return f"{parts.scheme}://{parts.netloc}"

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: str) -> str:
        if not value.startswith(_DATABASE_SCHEMES):
            raise ValueError("must be a sqlite:// or postgresql URL (ADR-005)")
        return value

    @field_validator("token_hash_key")
    @classmethod
    def _check_token_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < MIN_TOKEN_HASH_KEY_BYTES:
            raise ValueError(f"must be at least {MIN_TOKEN_HASH_KEY_BYTES} bytes")
        return value

    @model_validator(mode="after")
    def _check_cross_field_rules(self) -> Self:
        problems: list[str] = []
        if self.max_case_storage_mb < self.max_upload_mb:
            problems.append("MAX_CASE_STORAGE_MB must be at least MAX_UPLOAD_MB")
        if self.email_mode is EmailMode.SMTP:
            if not self.smtp_host or not self.email_from:
                problems.append("EMAIL_MODE=smtp requires SMTP_HOST and EMAIL_FROM")
            if (self.smtp_username is None) != (self.smtp_password is None):
                problems.append("SMTP_USERNAME and SMTP_PASSWORD must be set together")
        if self.verification_mode is VerificationMode.SANDBOX and not (
            self.cashfree_client_id and self.cashfree_client_secret and self.cashfree_base_url
        ):
            problems.append(
                "VERIFICATION_MODE=sandbox requires CASHFREE_CLIENT_ID, "
                "CASHFREE_CLIENT_SECRET and CASHFREE_BASE_URL"
            )
        if (
            self.auth_login_ip_limit_per_hour > DEFAULT_LOGIN_IP_LIMIT_PER_HOUR
            and self.app_env is not AppEnv.TEST
        ):
            problems.append(
                f"AUTH_LOGIN_IP_LIMIT_PER_HOUR may exceed {DEFAULT_LOGIN_IP_LIMIT_PER_HOUR} "
                "only with APP_ENV=test"
            )
        if self.app_env is AppEnv.PRODUCTION:
            problems.extend(self._production_problems())
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def _production_problems(self) -> list[str]:
        problems: list[str] = []
        if not self.public_base_url.startswith("https://"):
            problems.append("PUBLIC_BASE_URL must use https in production")
        if self.token_hash_key.get_secret_value() == _EXAMPLE_TOKEN_HASH_KEY:
            problems.append("TOKEN_HASH_KEY must not be the example value in production")
        if self.auth_signup_limit_per_hour > DEFAULT_SIGNUP_LIMIT_PER_HOUR:
            problems.append(
                f"AUTH_SIGNUP_LIMIT_PER_HOUR must not exceed {DEFAULT_SIGNUP_LIMIT_PER_HOUR} "
                "in production"
            )
        if self.nonlive_adapters and not self.allow_nonlive_verified:
            problems.append(
                f"non-live adapters in production ({', '.join(self.nonlive_adapters)}); "
                "set ALLOW_NONLIVE_VERIFIED=1 to allow them with the simulated banner"
            )
        return problems

    @property
    def nonlive_adapters(self) -> tuple[str, ...]:
        """Adapters whose results are not real: shown as "simulated" everywhere."""
        adapters: list[str] = []
        if self.email_mode is EmailMode.SIMULATED:
            adapters.append("email=simulated")
        if self.verification_mode in (VerificationMode.SIMULATED, VerificationMode.SANDBOX):
            adapters.append(f"verification={self.verification_mode.value}")
        return tuple(adapters)

    @property
    def login_ip_limit_per_hour(self) -> int:
        """The login limit to enforce. Defence in depth for settings built without validation
        (e.g. `model_copy`): outside APP_ENV=test a raised value falls back to the default."""
        if self.app_env is AppEnv.TEST:
            return self.auth_login_ip_limit_per_hour
        return min(self.auth_login_ip_limit_per_hour, DEFAULT_LOGIN_IP_LIMIT_PER_HOUR)

    @property
    def show_simulated_banner(self) -> bool:
        return bool(self.nonlive_adapters)


def load_settings(**overrides: object) -> Settings:
    """Build settings from the environment (and `.env`), raising a log-safe `ConfigError`."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ConfigError(_describe(exc)) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, loaded once. Tests pass explicit settings instead."""
    return load_settings()


def _describe(exc: ValidationError) -> str:
    lines = ["Invalid PaySetu configuration:"]
    for error in exc.errors(include_input=False, include_url=False):
        name = ".".join(str(part) for part in error["loc"]).upper() or "SETTINGS"
        reason = error["msg"].removeprefix("Value error, ")
        lines.append(f"  - {name}: {reason}")
    return "\n".join(lines)
