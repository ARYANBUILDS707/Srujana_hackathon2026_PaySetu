"""Session token primitives (ARCHITECTURE.md 8.1; DATABASE.md 3.2).

A session token is 32 random bytes (256 bits), URL-safe base64. Only its SHA-256 hash is
stored; the raw value exists only in the HttpOnly `ps_session` cookie. Client IPs are stored
only as an HMAC under TOKEN_HASH_KEY.
"""

import hashlib
import hmac
import secrets

from app.config import Settings

SESSION_COOKIE = "ps_session"
TOKEN_BYTES = 32
MAX_TOKEN_LENGTH = 128  # longer cookie values are rejected without a lookup
USER_AGENT_MAX = 200
SLIDE_INTERVAL_SECONDS = 3600  # last_seen_at is refreshed at most hourly


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ip_hash(settings: Settings, ip: str) -> str:
    key = settings.token_hash_key.get_secret_value().encode("utf-8")
    return hmac.new(key, ip.encode("utf-8"), hashlib.sha256).hexdigest()


def keyed_hash(settings: Settings, token: str) -> str:
    """HMAC-SHA256 under TOKEN_HASH_KEY: used for password-reset tokens, so a copy of the
    database alone cannot be used to confirm a guessed token."""
    key = settings.token_hash_key.get_secret_value().encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def cookie_secure(settings: Settings) -> bool:
    """`Secure` whenever the browser-facing origin is https (always, in production)."""
    return settings.public_base_url.startswith("https://")


def clear_cookie_header(settings: Settings) -> str:
    """A Set-Cookie value that removes the session cookie (used on 401 responses)."""
    secure = "; Secure" if cookie_secure(settings) else ""
    return f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=lax{secure}"
