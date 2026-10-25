"""Password hashing and policy (ARCHITECTURE.md 8.1; API.md Section 4).

Argon2id with the `argon2-cffi` defaults. Passwords are never logged, returned or stored in
plain text. `verify_password` always runs one Argon2 verification, even for an unknown email
(against a fixed dummy hash), so response time does not reveal whether an account exists.
"""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

# A small bundled list of common passwords that meet the length rule (ARCHITECTURE.md 8.1).
# Compared case-insensitively. Not exhaustive: it stops the most obvious choices only.
COMMON_PASSWORDS = frozenset(
    {
        "0000000000",
        "0123456789",
        "0987654321",
        "1111111111",
        "1122334455",
        "1234512345",
        "1234567890",
        "12345678910",
        "123456789a",
        "1q2w3e4r5t",
        "1qaz2wsx3edc",
        "9876543210",
        "a123456789",
        "aaaaaaaaaa",
        "abc1234567",
        "abcd123456",
        "abcdefghij",
        "admin12345",
        "admin@1234",
        "administrator",
        "asdfghjkl1",
        "changeme123",
        "football123",
        "iloveyou12",
        "india12345",
        "india@1234",
        "letmein1234",
        "password01",
        "password12",
        "password123",
        "password1234",
        "password@123",
        "passw0rd123",
        "paysetu123",
        "paysetu1234",
        "qwerty1234",
        "qwerty12345",
        "qwertyuiop",
        "qwertyuiop1",
        "sunshine123",
        "welcome123",
        "welcome@123",
        "zaq12wsxcde",
    }
)

_hasher = PasswordHasher()


def password_problem(password: str) -> str | None:
    """A user-safe reason the password is not acceptable, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Use at most {MAX_PASSWORD_LENGTH} characters."
    if password.lower() in COMMON_PASSWORDS:
        return "This password is too common. Choose a less predictable one."
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _hasher.hash("paysetu-timing-equaliser-not-a-real-password")


def verify_password(password_hash: str | None, password: str) -> bool:
    """True if `password` matches. With no hash (unknown account) it still does the work."""
    try:
        return _hasher.verify(password_hash or _dummy_hash(), password) and bool(password_hash)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
