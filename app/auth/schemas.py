from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    # An ID token from Google Identity Services (a signed JWT), not an
    # access token or authorization code — see docs/DECISIONS.md ADR-011.
    id_token: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    tier: str


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class GenericSuccessResponse(BaseModel):
    """Deliberately identical regardless of whether the target email exists
    — enumeration-safe, per docs/SECURITY.md §2."""

    message: str = "If an account with that email exists, we've sent instructions."
