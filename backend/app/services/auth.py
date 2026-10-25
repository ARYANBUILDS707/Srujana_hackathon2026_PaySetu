"""Accounts, sessions and the supplier principal (Phase 6; ARCHITECTURE.md Section 8).

- Signup creates a user, the user's supplier (owner = that user) and a session, in one
  transaction. Ownership always comes from the session, never from request data.
- Login errors are generic and take the same time whether or not the account exists.
- Sessions expire after SESSION_IDLE_HOURS without use (sliding, refreshed at most hourly) and
  SESSION_ABSOLUTE_DAYS after login, and are revoked by logout.
- Phase 6.1: password reset by emailed single-use token, password change and sign-out
  everywhere. Every password change (either way) revokes all of the user's sessions.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.config import Settings
from app.db import Database
from app.errors import BadRequest, Conflict, FieldError, Unauthenticated, ValidationFailed
from app.mail import templates
from app.mail.senders import EmailSender, deliver
from app.models import PasswordResetToken, Supplier, User, UserSession
from app.schemas import auth as schemas
from app.security import passwords
from app.security import sessions as tokens

GENERIC_LOGIN_ERROR = "Email or password is incorrect."
GENERIC_SIGNUP_CONFLICT = "Could not create an account with these details."


@dataclass(frozen=True)
class SupplierPrincipal:
    """Who is calling: resolved from the session cookie on every supplier request."""

    user_id: str
    supplier_id: str
    session_id: str


@dataclass(frozen=True)
class ClientInfo:
    ip: str
    user_agent: str | None


@dataclass(frozen=True)
class SessionGrant:
    me: schemas.MeOut
    token: str  # raw cookie value; never stored or logged


def _now(clock: Clock) -> str:
    return format_utc_timestamp(clock.now_utc())


def _parse(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp)


def _me(user: User, supplier: Supplier) -> schemas.MeOut:
    return schemas.MeOut(
        user=schemas.UserOut(id=user.id, email=user.email, full_name=user.full_name),
        supplier=schemas.AccountSupplierOut(
            id=supplier.id, legal_name=supplier.legal_name, demo_mode=supplier.is_demo
        ),
    )


def _owned_supplier(session: Session, user_id: str) -> Supplier | None:
    return session.scalars(select(Supplier).where(Supplier.owner_user_id == user_id)).first()


def _start_session(
    session: Session, clock: Clock, settings: Settings, user: User, client: ClientInfo
) -> str:
    token = tokens.new_token()
    now = clock.now_utc()
    session.add(
        UserSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=tokens.token_hash(token),
            created_at=format_utc_timestamp(now),
            last_seen_at=format_utc_timestamp(now),
            expires_at=format_utc_timestamp(now + timedelta(days=settings.session_absolute_days)),
            revoked_at=None,
            user_agent=(client.user_agent or "")[: tokens.USER_AGENT_MAX] or None,
            ip_hash=tokens.ip_hash(settings, client.ip),
        )
    )
    return token


def signup(
    session: Session,
    clock: Clock,
    settings: Settings,
    data: schemas.SignupIn,
    client: ClientInfo,
) -> SessionGrant:
    # Hash before the duplicate check, so both paths cost the same.
    password_hash = passwords.hash_password(data.password)
    now = _now(clock)
    try:
        with session.begin():
            if session.scalars(select(User).where(User.email == data.email)).first():
                raise Conflict(GENERIC_SIGNUP_CONFLICT)
            user = User(
                id=str(uuid.uuid4()),
                email=data.email,
                password_hash=password_hash,
                full_name=data.full_name,
                terms_version=data.accept_terms_version,
                terms_accepted_at=now,
                is_active=True,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.flush()
            supplier = Supplier(
                id=str(uuid.uuid4()),
                owner_user_id=user.id,
                legal_name=data.business_name,
                trade_name=None,
                udyam_number=None,
                enterprise_class=None,
                major_activity=None,
                udyam_registration_date=None,
                udyam_verification_status="self_declared",
                gstin=None,
                contact_email=data.email,
                is_demo=False,
                created_at=now,
                updated_at=now,
            )
            session.add(supplier)
            token = _start_session(session, clock, settings, user, client)
            return SessionGrant(_me(user, supplier), token)
    except IntegrityError:  # a concurrent signup with the same email
        raise Conflict(GENERIC_SIGNUP_CONFLICT) from None


def login(
    session: Session,
    clock: Clock,
    settings: Settings,
    data: schemas.LoginIn,
    client: ClientInfo,
    previous_token: str | None,
) -> SessionGrant:
    with session.begin():
        user = session.scalars(select(User).where(User.email == data.email)).first()
        # Always one Argon2 verification, so timing does not reveal whether the email exists.
        valid = passwords.verify_password(user.password_hash if user else None, data.password)
        if user is None or not valid or not user.is_active:
            raise Unauthenticated(GENERIC_LOGIN_ERROR, code="invalid_credentials")
        supplier = _owned_supplier(session, user.id)
        if supplier is None:
            raise Unauthenticated(GENERIC_LOGIN_ERROR, code="invalid_credentials")
        if passwords.needs_rehash(user.password_hash):
            user.password_hash = passwords.hash_password(data.password)
        now = _now(clock)
        user.last_login_at = now
        user.updated_at = now
        if previous_token:  # no session fixation: a login always starts a fresh session
            _revoke(session, previous_token, now)
        token = _start_session(session, clock, settings, user, client)
        return SessionGrant(_me(user, supplier), token)


def _revoke(session: Session, token: str, now: str) -> None:
    if len(token) > tokens.MAX_TOKEN_LENGTH:
        return
    row = session.scalars(
        select(UserSession).where(UserSession.token_hash == tokens.token_hash(token))
    ).first()
    if row is not None and row.revoked_at is None:
        row.revoked_at = now


def logout(session: Session, clock: Clock, token: str | None) -> None:
    """Revoke the session behind `token`, if any. Idempotent."""
    if not token:
        return
    with session.begin():
        _revoke(session, token, _now(clock))


def resolve(
    session: Session, clock: Clock, settings: Settings, token: str | None
) -> SupplierPrincipal:
    """The principal for a session cookie, or `Unauthenticated` (401)."""
    clear = {"Set-Cookie": tokens.clear_cookie_header(settings)}
    if not token or len(token) > tokens.MAX_TOKEN_LENGTH:
        raise Unauthenticated("Sign in to continue.", headers=clear if token else None)
    with session.begin():
        row = session.scalars(
            select(UserSession).where(UserSession.token_hash == tokens.token_hash(token))
        ).first()
        if row is None or row.revoked_at is not None:
            raise Unauthenticated("Sign in to continue.", headers=clear)
        now = clock.now_utc()
        idle_deadline = _parse(row.last_seen_at) + timedelta(hours=settings.session_idle_hours)
        if now >= _parse(row.expires_at) or now >= idle_deadline:
            raise Unauthenticated(
                "Your session has expired. Sign in again.", code="session_expired", headers=clear
            )
        user = session.get(User, row.user_id)
        supplier = _owned_supplier(session, row.user_id)
        if user is None or not user.is_active or supplier is None:
            raise Unauthenticated("Sign in to continue.", headers=clear)
        if (now - _parse(row.last_seen_at)).total_seconds() >= tokens.SLIDE_INTERVAL_SECONDS:
            row.last_seen_at = format_utc_timestamp(now)
        return SupplierPrincipal(user_id=user.id, supplier_id=supplier.id, session_id=row.id)


def me(session: Session, principal: SupplierPrincipal) -> schemas.MeOut:
    with session.begin():
        user = session.get(User, principal.user_id)
        supplier = session.get(Supplier, principal.supplier_id)
        if user is None or supplier is None:  # pragma: no cover - resolve() checked both
            raise Unauthenticated("Sign in to continue.")
        return _me(user, supplier)


def create_demo_account(session: Session, clock: Clock, email: str, password: str) -> str:
    """Give the seeded demo supplier a login (operator action; `make demo-account`).

    Explicit and narrow: it only ever assigns a supplier marked `is_demo` that has no owner,
    and never touches any other row. Returns the new user's ID.
    """
    problem = passwords.password_problem(password)
    if problem:
        raise ValueError(f"DEMO_ACCOUNT_PASSWORD: {problem}")
    normalised = schemas.LoginIn(email=email, password=password).email
    if not schemas.valid_email(normalised):
        raise ValueError("DEMO_ACCOUNT_EMAIL is not a valid email address.")
    password_hash = passwords.hash_password(password)
    now = _now(clock)
    with session.begin():
        supplier = session.scalars(
            select(Supplier)
            .where(Supplier.is_demo.is_(True), Supplier.owner_user_id.is_(None))
            .order_by(Supplier.created_at)
        ).first()
        if supplier is None:
            raise ValueError("No unowned demo supplier. Run `make seed` first.")
        if session.scalars(select(User).where(User.email == normalised)).first():
            raise ValueError("An account with this email already exists.")
        user = User(
            id=str(uuid.uuid4()),
            email=normalised,
            password_hash=password_hash,
            full_name="Demo supplier (synthetic)",
            terms_version=schemas.CURRENT_TERMS_VERSION,
            terms_accepted_at=now,
            is_active=True,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        supplier.owner_user_id = user.id
        supplier.updated_at = now
        return user.id


# ------------------------------------------------------------------ Phase 6.1: passwords

RESET_TOKEN_MINUTES = 15
FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for this email, PaySetu will send it a link to reset the password. "
    "The link works once and expires after 15 minutes."
)
INVALID_RESET_TOKEN = "This reset link is invalid, has expired or has already been used."


@dataclass(frozen=True)
class PendingReset:
    """A reset token waiting to be emailed. `token` is the raw value: never store or log it."""

    token_id: str
    user_id: str
    email: str
    token: str


@dataclass(frozen=True)
class PasswordUpdate:
    user_id: str
    email: str
    changed_at: datetime


def _revoke_all_sessions(session: Session, user_id: str, now: str) -> None:
    session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def _revoke_reset_tokens(session: Session, user_id: str, now: str) -> None:
    session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


def request_password_reset(
    session: Session, clock: Clock, settings: Settings, email: str, client: ClientInfo
) -> PendingReset | None:
    """Issue a new reset token for an active account; None (silently) for any other email.

    Issuing a token revokes every earlier unused one for that account.
    """
    with session.begin():
        user = session.scalars(select(User).where(User.email == email)).first()
        if user is None or not user.is_active:
            return None
        now = clock.now_utc()
        _revoke_reset_tokens(session, user.id, format_utc_timestamp(now))
        token = tokens.new_token()
        row = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=tokens.keyed_hash(settings, token),
            created_at=format_utc_timestamp(now),
            expires_at=format_utc_timestamp(now + timedelta(minutes=RESET_TOKEN_MINUTES)),
            used_at=None,
            revoked_at=None,
            ip_hash=tokens.ip_hash(settings, client.ip),
        )
        session.add(row)
        return PendingReset(row.id, user.id, user.email, token)


def reset_link(settings: Settings, token: str) -> str:
    # The token travels in the URL fragment: browsers never send fragments to a server or in
    # a Referer header, so it stays out of access logs and third-party requests.
    return f"{settings.public_base_url}/reset-password#token={token}"


def deliver_password_reset(
    database: Database, sender: EmailSender, settings: Settings, clock: Clock, pending: PendingReset
) -> bool:
    """Email the reset link (run after the response is sent). If delivery fails the token is
    revoked, so no link that the user never received stays valid."""
    message = templates.password_reset(
        pending.email, reset_link(settings, pending.token), RESET_TOKEN_MINUTES
    )
    if deliver(sender, message, pending.user_id):
        return True
    with database.session() as session, session.begin():
        session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == pending.token_id, PasswordResetToken.used_at.is_(None))
            .values(revoked_at=_now(clock))
        )
    return False


def reset_password(
    session: Session, clock: Clock, settings: Settings, data: schemas.ResetPasswordIn
) -> PasswordUpdate:
    """Consume the token and set the new password in one transaction; revoke every session.

    Consumption is a single conditional UPDATE (`used_at IS NULL AND revoked_at IS NULL AND
    expires_at > now`), so of two concurrent requests with the same token exactly one wins.
    """
    new_hash = passwords.hash_password(data.new_password)  # slow; outside the transaction
    if len(data.token) > tokens.MAX_TOKEN_LENGTH:
        raise BadRequest(INVALID_RESET_TOKEN, code="invalid_reset_token")
    token_hash = tokens.keyed_hash(settings, data.token)
    with session.begin():
        now_dt = clock.now_utc()
        now = format_utc_timestamp(now_dt)
        result = session.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .values(used_at=now)
            .execution_options(synchronize_session=False)
        )
        consumed = cast(CursorResult[Any], result).rowcount == 1
        row = (
            session.scalars(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
            ).first()
            if consumed
            else None
        )
        user = session.get(User, row.user_id) if row is not None else None
        if user is None or not user.is_active:
            raise BadRequest(INVALID_RESET_TOKEN, code="invalid_reset_token")
        user.password_hash = new_hash
        user.updated_at = now
        _revoke_all_sessions(session, user.id, now)
        _revoke_reset_tokens(session, user.id, now)
        return PasswordUpdate(user.id, user.email, now_dt)


def change_password(
    session: Session,
    clock: Clock,
    settings: Settings,
    principal: SupplierPrincipal,
    data: schemas.ChangePasswordIn,
    client: ClientInfo,
) -> tuple[PasswordUpdate, str]:
    """Verify the current password, set the new one, revoke EVERY session of the user
    (including the one making the request) and start a fresh session for this browser.

    Security decision (DECISIONS.md Section 9): the caller stays signed in, but on a new
    session token, so a copy of the old cookie, wherever it is, stops working.
    """
    with session.begin():
        user = session.get(User, principal.user_id)
        current_hash = user.password_hash if user else None
    if user is None or not passwords.verify_password(current_hash, data.current_password):
        raise ValidationFailed(
            errors=[FieldError("current_password", "incorrect", "Current password is incorrect.")]
        )
    if passwords.verify_password(current_hash, data.new_password):
        raise ValidationFailed(
            errors=[
                FieldError(
                    "new_password",
                    "unchanged",
                    "Choose a password different from your current one.",
                )
            ]
        )
    new_hash = passwords.hash_password(data.new_password)
    with session.begin():
        user = session.get(User, principal.user_id)
        if user is None or user.password_hash != current_hash:
            # Changed by a concurrent request since we verified it: ask the user to retry.
            raise Conflict("Your password was just changed elsewhere. Sign in again.")
        now_dt = clock.now_utc()
        now = format_utc_timestamp(now_dt)
        user.password_hash = new_hash
        user.updated_at = now
        _revoke_all_sessions(session, user.id, now)
        _revoke_reset_tokens(session, user.id, now)
        token = _start_session(session, clock, settings, user, client)
        return PasswordUpdate(user.id, user.email, now_dt), token


def notify_password_changed(
    sender: EmailSender, settings: Settings, update_: PasswordUpdate, how: str
) -> bool:
    message = templates.password_changed(
        update_.email, update_.changed_at, how, f"{settings.public_base_url}/forgot-password"
    )
    return deliver(sender, message, update_.user_id)


def logout_all(session: Session, clock: Clock, principal: SupplierPrincipal) -> None:
    """Revoke every session of the current user, on every device."""
    with session.begin():
        _revoke_all_sessions(session, principal.user_id, _now(clock))
