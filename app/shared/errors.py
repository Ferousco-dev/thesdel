"""Stable, documented error codes. See docs/API.md §4 for the envelope shape.

Internal exception details (stack traces, DB errors, provider errors) never
reach the client — only `error_code` + a safe `message` do. Full detail goes
to structured logs keyed by request_id instead.
"""

from typing import Any

from fastapi import status


class AppError(Exception):
    """Base class for all application errors that map to a safe client response."""

    error_code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class UnauthenticatedError(AppError):
    error_code = "unauthenticated"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication required."


class InvalidCredentialsError(AppError):
    error_code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect email or password."


class TokenExpiredError(AppError):
    error_code = "token_expired"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Your session has expired. Please log in again."


class TokenInvalidError(AppError):
    error_code = "token_invalid"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid session. Please log in again."


class ForbiddenError(AppError):
    error_code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You don't have permission to do that."


class UpgradeRequiredError(AppError):
    error_code = "upgrade_required"
    status_code = status.HTTP_403_FORBIDDEN
    message = "This feature requires a higher tier."


class NotFoundError(AppError):
    error_code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(AppError):
    error_code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "This action conflicts with existing state."


class ValidationAppError(AppError):
    error_code = "validation_error"
    status_code = 422
    message = "Invalid input."


class RateLimitedError(AppError):
    error_code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many requests. Please slow down."


class CapReachedError(AppError):
    error_code = "cap_reached"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "You've used all your allowance for this period."


class ServiceUnavailableError(AppError):
    error_code = "service_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "A required service is temporarily unavailable."
