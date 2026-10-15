from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import settings
from app.dependencies import AuthServiceDep
from app.schemas.auth import AdminLoginRequest, AdminSessionResponse
from app.services.auth_service import (
    AuthenticationNotConfiguredError,
    InvalidCredentialsError,
    LoginRateLimitError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AdminSessionResponse)
def login(
    credentials: AdminLoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
) -> AdminSessionResponse:
    response.headers["Cache-Control"] = "no-store"
    client_key = request.client.host if request.client else "unknown"
    try:
        token, session = auth_service.login(
            credentials.username,
            credentials.password,
            client_key,
        )
    except AuthenticationNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="administrator authentication is not configured",
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid administrator credentials",
            headers={"WWW-Authenticate": "Cookie"},
        ) from exc
    except LoginRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many login attempts",
            headers={"Retry-After": str(settings.auth_login_window_seconds)},
        ) from exc

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/api",
    )
    return AdminSessionResponse(authenticated=True, username=session.username)


@router.get("/session", response_model=AdminSessionResponse)
def get_session(
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
) -> AdminSessionResponse:
    response.headers["Cache-Control"] = "no-store"
    session = auth_service.get_session(request.cookies.get(settings.auth_cookie_name))
    if not session:
        return AdminSessionResponse(authenticated=False)
    return AdminSessionResponse(authenticated=True, username=session.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
) -> None:
    response.headers["Cache-Control"] = "no-store"
    auth_service.logout(request.cookies.get(settings.auth_cookie_name))
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/api",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
    )
