"""Accounts and sessions (DATABASE.md Sections 3.1 and 3.2; Phase 6).

Passwords are stored only as Argon2id hashes and session tokens only as SHA-256 hashes; the raw
token lives in the browser's HttpOnly cookie. Timestamps are ISO-8601 UTC strings with a `Z`.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.entities import HASH, ID, TS


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-cased, trimmed
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    terms_version: Mapped[str] = mapped_column(String(32))
    terms_accepted_at: Mapped[str] = mapped_column(TS)
    is_active: Mapped[bool] = mapped_column(Boolean)
    # Phase 7A: set only when a verification (or password-reset) link sent to `email` is used.
    # Proves control of the inbox; nothing about the business, Udyam or MSMED eligibility.
    email_verified_at: Mapped[str | None] = mapped_column(TS)
    last_login_at: Mapped[str | None] = mapped_column(TS)
    created_at: Mapped[str] = mapped_column(TS)
    updated_at: Mapped[str] = mapped_column(TS)


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(HASH, unique=True)
    created_at: Mapped[str] = mapped_column(TS)
    last_seen_at: Mapped[str] = mapped_column(TS)
    expires_at: Mapped[str] = mapped_column(TS)  # absolute expiry
    revoked_at: Mapped[str | None] = mapped_column(TS)
    user_agent: Mapped[str | None] = mapped_column(String(200))
    ip_hash: Mapped[str | None] = mapped_column(HASH)  # HMAC of the IP; never the raw IP


class PasswordResetToken(Base):
    """A single-use, 15-minute password-reset token (DATABASE.md 3.3; Phase 6.1).

    Only an HMAC of the token (key TOKEN_HASH_KEY) is stored. `used_at` marks consumption;
    `revoked_at` marks a token superseded by a newer request, a password change, or a failed
    delivery. A token is valid only while both are null and `expires_at` is in the future.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(HASH, unique=True)
    created_at: Mapped[str] = mapped_column(TS)
    expires_at: Mapped[str] = mapped_column(TS)
    used_at: Mapped[str | None] = mapped_column(TS)
    revoked_at: Mapped[str | None] = mapped_column(TS)
    ip_hash: Mapped[str | None] = mapped_column(HASH)  # HMAC of the requesting IP


class EmailVerificationToken(Base):
    """A single-use email-verification token (Phase 7A); same pattern as password resets.

    Only an HMAC of the token (key TOKEN_HASH_KEY) is stored. `email` records the address the
    link was sent to: the token verifies the user only while that is still their address.
    """

    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(254))
    token_hash: Mapped[str] = mapped_column(HASH, unique=True)
    created_at: Mapped[str] = mapped_column(TS)
    expires_at: Mapped[str] = mapped_column(TS)
    used_at: Mapped[str | None] = mapped_column(TS)
    revoked_at: Mapped[str | None] = mapped_column(TS)
