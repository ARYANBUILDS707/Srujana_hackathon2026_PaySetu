"""Shared FastAPI dependencies: the request's database session, clock and principal.

`current_principal` is the auth dependency for every supplier route (AGENTS.md 8.3-8.4): it
resolves the `ps_session` cookie to a `SupplierPrincipal`, or answers 401. Routes pass
`principal.supplier_id` to services, which scope every query by it; another supplier's rows
are indistinguishable from missing rows (404).
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.clock import Clock, get_clock
from app.config import Settings
from app.db import get_session
from app.errors import Forbidden
from app.security.rate_limit import RateLimitCategory, RateLimiter, client_ip
from app.security.sessions import SESSION_COOKIE
from app.services import auth as auth_service
from app.services.auth import ClientInfo, SupplierPrincipal

SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
LimiterDep = Annotated[RateLimiter, Depends(get_limiter)]


def client_info(request: Request) -> ClientInfo:
    return ClientInfo(ip=client_ip(request.scope), user_agent=request.headers.get("user-agent"))


def current_principal(
    request: Request,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> SupplierPrincipal:
    principal = auth_service.resolve(session, clock, settings, request.cookies.get(SESSION_COOKIE))
    limiter.hit(RateLimitCategory.DEFAULT_USER, principal.user_id)
    return principal


PrincipalDep = Annotated[SupplierPrincipal, Depends(current_principal)]


def verified_principal(principal: PrincipalDep) -> SupplierPrincipal:
    """Phase 7A: the case workspace (cases, buyers, evidence, packs, supplier profile)
    requires a verified email. 403 `email_not_verified` otherwise; account routes (me,
    resend, change password, sign out) use `PrincipalDep` and stay available."""
    if not principal.email_verified:
        raise Forbidden(
            "Confirm your email address to use the case workspace.", code="email_not_verified"
        )
    return principal


VerifiedPrincipalDep = Annotated[SupplierPrincipal, Depends(verified_principal)]
