"""Authentication endpoints (API.md Section 2.2; Phase 6).

Sessions live in the `ps_session` cookie: HttpOnly, SameSite=Lax, Path=/, Secure on https.
Phase 6.1 adds forgot-password, reset-password, change-password and logout-all.
The raw token is never returned in a body. Unsafe methods here pass the same CSRF check as
every other cookie route (Origin + `X-PaySetu-Client: web`).
"""

from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import ClockDep, LimiterDep, PrincipalDep, SessionDep, SettingsDep, client_info
from app.config import Settings
from app.mail.senders import EmailSender
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


# ------------------------------------------------------------------ Phase 6.1: passwords


def _sender(request: Request) -> EmailSender:
    sender: EmailSender = request.app.state.email_sender
    return sender


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=cookie_secure(settings), httponly=True, samesite="lax"
    )


@router.post("/forgot-password", response_model=schemas.ForgotPasswordOut, status_code=202)
def forgot_password(
    data: schemas.ForgotPasswordIn,
    request: Request,
    response: Response,
    background: BackgroundTasks,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> schemas.ForgotPasswordOut:
    """Always 202 with the same body, whether or not the account exists (no enumeration).

    The email is sent after the response, so response time does not depend on the provider;
    a failed delivery is logged and its token revoked, but never reported to the caller.
    """
    ip = client_ip(request.scope)
    limiter.hit(RateLimitCategory.PASSWORD_FORGOT_IP, ip)
    limiter.hit(RateLimitCategory.PASSWORD_FORGOT, f"{ip}|{data.email}")
    pending = service.request_password_reset(
        session, clock, settings, data.email, client_info(request)
    )
    if pending is not None:
        background.add_task(
            service.deliver_password_reset,
            request.app.state.database,
            _sender(request),
            settings,
            clock,
            pending,
        )
    _no_store(response)
    return schemas.ForgotPasswordOut(detail=service.FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=schemas.PasswordUpdatedOut)
def reset_password(
    data: schemas.ResetPasswordIn,
    request: Request,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> Response:
    """Set a new password with a valid token. Signs out every session; does not sign in."""
    limiter.hit(RateLimitCategory.PASSWORD_RESET, client_ip(request.scope))
    update_ = service.reset_password(session, clock, settings, data)
    sent = service.notify_password_changed(_sender(request), settings, update_, "reset")
    response = JSONResponse(
        schemas.PasswordUpdatedOut(notification="sent" if sent else "failed").model_dump(),
        headers={"Cache-Control": "no-store"},
    )
    _clear_session_cookie(response, settings)
    return response


@router.post("/change-password", response_model=schemas.PasswordUpdatedOut)
def change_password(
    data: schemas.ChangePasswordIn,
    principal: PrincipalDep,
    request: Request,
    response: Response,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> schemas.PasswordUpdatedOut:
    """Change the password; all sessions are revoked and this browser gets a new one."""
    limiter.hit(RateLimitCategory.PASSWORD_CHANGE, principal.user_id)
    update_, token = service.change_password(
        session, clock, settings, principal, data, client_info(request)
    )
    _set_session_cookie(response, settings, token)
    _no_store(response)
    sent = service.notify_password_changed(_sender(request), settings, update_, "changed")
    return schemas.PasswordUpdatedOut(notification="sent" if sent else "failed")


@router.post("/logout-all", status_code=204)
def logout_all(
    principal: PrincipalDep, session: SessionDep, clock: ClockDep, settings: SettingsDep
) -> Response:
    """Revoke every session of the current user (all devices) and clear this cookie."""
    service.logout_all(session, clock, principal)
    response = Response(status_code=204)
    _clear_session_cookie(response, settings)
    return response
