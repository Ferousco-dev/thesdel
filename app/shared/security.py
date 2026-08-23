"""Password hashing (Argon2id) and JWT access-token issuing/verification.

See docs/DECISIONS.md ADR-002 and docs/SECURITY.md §2. Refresh tokens are
handled in app/auth/service.py — they are opaque, hashed-at-rest, rotated
on use, not JWTs.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.shared.config import get_settings
from app.shared.errors import TokenExpiredError, TokenInvalidError, UnauthenticatedError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def generate_opaque_token() -> str:
    """Used for refresh tokens, email verification, and password reset tokens.
    Never stored in plaintext — callers hash before persisting."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    """SHA-256 is fine here (not a password) — the token itself already has
    high entropy from secrets.token_urlsafe; this hash is purely so a DB
    leak doesn't hand out usable tokens."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(*, user_id: str, tier: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "tier": tier,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError() from exc

    if payload.get("type") != "access":
        raise TokenInvalidError()
    return payload


def verify_google_id_token(token: str) -> dict[str, Any]:
    """Verifies a Google Identity Services ID token: signature (against
    Google's published public keys, fetched over HTTPS), expiry, issuer,
    and audience (must match our own Client ID — this is what stops a
    valid token issued to a *different* app from being replayed here).
    See docs/DECISIONS.md ADR-011.
    """
    settings = get_settings()
    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except (GoogleAuthError, ValueError) as exc:
        raise UnauthenticatedError("Could not verify Google sign-in.") from exc

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise UnauthenticatedError("Could not verify Google sign-in.")
    if not claims.get("email"):
        raise UnauthenticatedError("Google did not provide an email address.")

    return claims
