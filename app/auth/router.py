from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.auth.schemas import (
    GenericSuccessResponse,
    GoogleAuthRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenPairResponse,
    UserPublic,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.shared.config import Settings, get_settings
from app.shared.db import get_db
from app.shared.rate_limit import check_rate_limit
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def get_auth_service(settings: Annotated[Settings, Depends(get_settings)]) -> AuthService:
    return AuthService(get_db(), settings)


async def _rate_limit_auth_endpoint(
    request: Request,
    bucket: str,
    *,
    max_requests: int | None = None,
    window_seconds: int | None = None,
) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    default_max = settings.rate_limit_login_max
    default_window = settings.rate_limit_login_window_seconds
    await check_rate_limit(
        get_redis(),
        key=f"ratelimit:auth:{bucket}:{client_ip}",
        max_requests=max_requests if max_requests is not None else default_max,
        window_seconds=window_seconds if window_seconds is not None else default_window,
        fail_closed=True,  # auth endpoints fail closed — see docs/ARCHITECTURE.md §7
    )


class RegisterResponse(TokenPairResponse):
    user: UserPublic


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterResponse:
    await _rate_limit_auth_endpoint(request, "register")
    tokens, user = await service.register(
        email=body.email, password=body.password, display_name=body.display_name
    )
    return RegisterResponse(**tokens.model_dump(), user=user)


class LoginResponse(TokenPairResponse):
    user: UserPublic


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    await _rate_limit_auth_endpoint(request, "login")
    tokens, user = await service.login(email=body.email, password=body.password)
    return LoginResponse(**tokens.model_dump(), user=user)


@router.post("/google", response_model=LoginResponse)
async def google_auth(
    body: GoogleAuthRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    # Same login-endpoint rate limit — this is a login path too, and a
    # forged/expired-token brute-force attempt should be throttled the
    # same way a password-guessing attempt is.
    await _rate_limit_auth_endpoint(request, "google")
    tokens, user = await service.google_login(id_token=body.id_token)
    return LoginResponse(**tokens.model_dump(), user=user)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    await _rate_limit_auth_endpoint(request, "refresh")
    return await service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.logout(body.refresh_token)


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    body: VerifyEmailRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    # Idempotent-success: already-verified is not an error — see
    # AuthService.verify_email.
    await service.verify_email(body.token)
    return {"status": "verified"}


@router.post("/resend-verification", response_model=GenericSuccessResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenericSuccessResponse:
    await _rate_limit_auth_endpoint(
        request,
        "resend_verification",
        max_requests=settings.rate_limit_verification_max,
        window_seconds=settings.rate_limit_verification_window_seconds,
    )
    await service.resend_verification(body.email)
    return GenericSuccessResponse()


@router.post("/password-reset/request", response_model=GenericSuccessResponse)
async def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenericSuccessResponse:
    await _rate_limit_auth_endpoint(
        request,
        "password_reset_request",
        max_requests=settings.rate_limit_password_reset_max,
        window_seconds=settings.rate_limit_password_reset_window_seconds,
    )
    # Always a generic success — enumeration-safe, see AuthService.request_password_reset.
    await service.request_password_reset(body.email)
    return GenericSuccessResponse()


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    await _rate_limit_auth_endpoint(
        request,
        "password_reset_confirm",
        max_requests=settings.rate_limit_password_reset_max,
        window_seconds=settings.rate_limit_password_reset_window_seconds,
    )
    await service.confirm_password_reset(token=body.token, new_password=body.new_password)
    return {"status": "reset"}
