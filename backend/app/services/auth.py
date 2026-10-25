"""Accounts, sessions and the supplier principal (Phase 6; ARCHITECTURE.md Section 8).

- Signup creates a user, the user's supplier (owner = that user) and a session, in one
  transaction. Ownership always comes from the session, never from request data.
- Login errors are generic and take the same time whether or not the account exists.
- Sessions expire after SESSION_IDLE_HOURS without use (sliding, refreshed at most hourly) and
  SESSION_ABSOLUTE_DAYS after login, and are revoked by logout.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.config import Settings
from app.errors import Conflict, Unauthenticated
from app.models import Supplier, User, UserSession
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
