"""Request and response schemas for authentication (API.md Section 2.2; Phase 6)."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.security.passwords import MAX_PASSWORD_LENGTH, password_problem

# The notice a new user accepts (shown on the signup page). Bump it when that text changes.
CURRENT_TERMS_VERSION = "evaluation-2026-10"

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")


def valid_email(email: str) -> bool:
    return len(email) <= 254 and _EMAIL.fullmatch(email) is not None


def _normalise_email(value: str) -> str:
    email = value.strip().lower()
    if not valid_email(email):
        raise ValueError("Enter a valid email address.")
    return email


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignupIn(_In):
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    business_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    email: str
    password: str
    accept_terms_version: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _normalise_email(value)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        problem = password_problem(value)
        if problem:
            raise ValueError(problem)
        return value

    @field_validator("accept_terms_version")
    @classmethod
    def _terms(cls, value: str) -> str:
        if value != CURRENT_TERMS_VERSION:
            raise ValueError("Accept the evaluation notice to create an account.")
        return value


class LoginIn(_In):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254)]
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    # Whether the user has proved control of `email` (recorded by a password reset, or by
    # the retired verification links). Informational only: it gates nothing.
    email_verified: bool


class AccountSupplierOut(BaseModel):
    id: str
    legal_name: str
    demo_mode: bool


class MeOut(BaseModel):
    user: UserOut
    supplier: AccountSupplierOut


class _NewPassword(_In):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        problem = password_problem(value)
        if problem:
            raise ValueError(problem)
        return value


class ForgotPasswordIn(_In):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _normalise_email(value)


class ResetPasswordIn(_NewPassword):
    token: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(_NewPassword):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class ForgotPasswordOut(BaseModel):
    detail: str


class PasswordUpdatedOut(BaseModel):
    # Whether the confirmation email was accepted for delivery. Never claimed when it failed.
    notification: Literal["sent", "failed"]
