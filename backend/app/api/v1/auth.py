"""Authentication endpoints (API.md Section 2.2; Phase 6).

Sessions live in the `ps_session` cookie: HttpOnly, SameSite=Lax, Path=/, Secure on https.
The raw token is never returned in a body. Unsafe methods here pass the same CSRF check as
every other cookie route (Origin + `X-PaySetu-Client: web`).
"""

from fastapi import APIRouter, Request, Response

from app.api.deps import ClockDep, LimiterDep, PrincipalDep, SessionDep, SettingsDep, client_info
from app.config import Settings
from app.schemas import auth as schemas
from app.security.rate_limit import RateLimitCategory, client_ip
from app.security.sessions import SESSION_COOKIE, cookie_secure
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_absolute_days * 86400,
        path="/",
        secure=cookie_secure(settings),
        httponly=True,
        samesite="lax",
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post("/signup", response_model=schemas.MeOut, status_code=201)
def signup(
    data: schemas.SignupIn,
    request: Request,
    response: Response,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> schemas.MeOut:
    limiter.hit(RateLimitCategory.SIGNUP, client_ip(request.scope))
    grant = service.signup(session, clock, settings, data, client_info(request))
    _set_session_cookie(response, settings, grant.token)
    _no_store(response)
    return grant.me


@router.post("/login", response_model=schemas.MeOut)
def login(
    data: schemas.LoginIn,
    request: Request,
    response: Response,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> schemas.MeOut:
    ip = client_ip(request.scope)
    limiter.hit(RateLimitCategory.LOGIN_IP, ip)
    limiter.hit(RateLimitCategory.LOGIN_ACCOUNT, f"{ip}|{data.email}")
    grant = service.login(
        session, clock, settings, data, client_info(request), request.cookies.get(SESSION_COOKIE)
    )
    _set_session_cookie(response, settings, grant.token)
    _no_store(response)
    return grant.me


@router.post("/logout", status_code=204)
def logout(
    request: Request, session: SessionDep, clock: ClockDep, settings: SettingsDep
) -> Response:
    """Revoke the current session (if any) and clear the cookie. Idempotent."""
    service.logout(session, clock, request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=cookie_secure(settings), httponly=True, samesite="lax"
    )
    return response


@router.get("/me", response_model=schemas.MeOut)
def me(principal: PrincipalDep, response: Response, session: SessionDep) -> schemas.MeOut:
    _no_store(response)
    return service.me(session, principal)
