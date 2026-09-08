from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=8, max_length=128, description="User's password (8-128 characters)")
    display_name: str = Field(min_length=1, max_length=80, description="User's display name (1-80 characters)")


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(min_length=1, max_length=128, description="User's password")


class GoogleAuthRequest(BaseModel):
    # An ID token from Google Identity Services (a signed JWT), not an
    # access token or authorization code — see docs/DECISIONS.md ADR-011.
    id_token: str = Field(min_length=1, description="Google ID token (signed JWT)")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(description="Refresh token to obtain new access token")


class LogoutRequest(BaseModel):
    refresh_token: str = Field(description="Refresh token to invalidate")


class TokenPairResponse(BaseModel):
    access_token: str = Field(description="JWT access token for API requests")
    refresh_token: str = Field(description="Refresh token to obtain new access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class UserPublic(BaseModel):
    id: str = Field(description="User ID")
    email: EmailStr = Field(description="User's email address")
    display_name: str = Field(description="User's display name")
    tier: str = Field(description="User's subscription tier (free, pro, premium)")


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, description="Email verification token")


class ResendVerificationRequest(BaseModel):
    email: EmailStr = Field(description="Email address to resend verification to")


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(description="Email address for password reset request")


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=1, description="Password reset token from email")
    new_password: str = Field(min_length=8, max_length=128, description="New password (8-128 characters)")


class GenericSuccessResponse(BaseModel):
    """Deliberately identical regardless of whether the target email exists
    — enumeration-safe, per docs/SECURITY.md §2."""

    message: str = "If an account with that email exists, we've sent instructions."
