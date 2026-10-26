"""Reviewer provisioning (Phase 7C): the only code that creates or revokes reviewer grants.

Called by the operator CLI (`python -m tools.reviewer`), never by an HTTP route, so no request
payload can grant the role. Grants are append-only (a revoked grant stays as an audit record;
granting again adds a new row), and each records the operator label that issued it.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.models import ReviewerGrant, Supplier, User
from app.schemas.auth import valid_email
from app.security import passwords

# Staff accounts accept no supplier terms; the field records how the account was made.
STAFF_TERMS_VERSION = "staff-account-cli"


@dataclass(frozen=True)
class ReviewerRow:
    email: str
    full_name: str
    granted_at: str
    granted_by: str
    revoked_at: str | None
    owns_supplier: bool


def _normalise(email: str) -> str:
    normalised = email.strip().lower()
    if not valid_email(normalised):
        raise ValueError("Not a valid email address.")
    return normalised


def _operator(label: str) -> str:
    label = label.strip()
    if not label or len(label) > 120:
        raise ValueError("The operator label must be 1-120 characters.")
    return label


def _grant(session: Session, user: User, operator: str, now: str) -> None:
    try:
        with session.begin_nested():
            session.add(
                ReviewerGrant(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    granted_at=now,
                    granted_by=operator,
                    revoked_at=None,
                    revoked_by=None,
                )
            )
    except IntegrityError:  # the partial unique index: one active grant per user
        raise ValueError(f"{user.email} is already a reviewer.") from None


def create_reviewer(
    session: Session, clock: Clock, *, email: str, full_name: str, password: str, operator: str
) -> str:
    """Create a reviewer-only staff account (no supplier) with an active grant; its user ID."""
    problem = passwords.password_problem(password)
    if problem:
        raise ValueError(problem)
    name = full_name.strip()
    if not name or len(name) > 120:
        raise ValueError("The name must be 1-120 characters.")
    normalised, label = _normalise(email), _operator(operator)
    password_hash = passwords.hash_password(password)
    now = format_utc_timestamp(clock.now_utc())
    with session.begin():
        if session.scalars(select(User).where(User.email == normalised)).first():
            raise ValueError(
                "An account with this email already exists. Use `grant` to give it the role."
            )
        user = User(
            id=str(uuid.uuid4()),
            email=normalised,
            password_hash=password_hash,
            full_name=name,
            terms_version=STAFF_TERMS_VERSION,
            terms_accepted_at=now,
            is_active=True,
            email_verified_at=None,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        _grant(session, user, label, now)
        return user.id


def grant_reviewer(session: Session, clock: Clock, *, email: str, operator: str) -> None:
    """Give an existing account the reviewer role. It still cannot review its own business."""
    normalised, label = _normalise(email), _operator(operator)
    with session.begin():
        user = session.scalars(select(User).where(User.email == normalised)).first()
        if user is None or not user.is_active:
            raise ValueError("No active account with this email.")
        _grant(session, user, label, format_utc_timestamp(clock.now_utc()))


def revoke_reviewer(session: Session, clock: Clock, *, email: str, operator: str) -> None:
    """Revoke the active grant; it takes effect on the reviewer's next request."""
    normalised, label = _normalise(email), _operator(operator)
    with session.begin():
        grant = session.scalars(
            select(ReviewerGrant)
            .join(User, User.id == ReviewerGrant.user_id)
            .where(User.email == normalised, ReviewerGrant.revoked_at.is_(None))
        ).first()
        if grant is None:
            raise ValueError(f"{normalised} has no active reviewer grant.")
        grant.revoked_at = format_utc_timestamp(clock.now_utc())
        grant.revoked_by = label


def list_reviewers(session: Session) -> list[ReviewerRow]:
    with session.begin():
        rows = session.execute(
            select(ReviewerGrant, User)
            .join(User, User.id == ReviewerGrant.user_id)
            .order_by(ReviewerGrant.granted_at, ReviewerGrant.id)
        ).all()
        return [
            ReviewerRow(
                email=user.email,
                full_name=user.full_name,
                granted_at=grant.granted_at,
                granted_by=grant.granted_by,
                revoked_at=grant.revoked_at,
                owns_supplier=session.scalars(
                    select(Supplier.id).where(Supplier.owner_user_id == user.id)
                ).first()
                is not None,
            )
            for grant, user in rows
        ]
