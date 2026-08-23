from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserPublic,
)
from app.auth.service import AuthService
from app.shared.config import Settings, get_settings
from app.shared.db import get_db
from app.shared.rate_limit import check_rate_limit
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def get_auth_service(settings: Annotated[Settings, Depends(get_settings)]) -> AuthService:
    return AuthService(get_db(), settings)


async def _rate_limit_auth_endpoint(request: Request, bucket: str) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(
        get_redis(),
        key=f"ratelimit:auth:{bucket}:{client_ip}",
        max_requests=settings.rate_limit_login_max,
        window_seconds=settings.rate_limit_login_window_seconds,
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
