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

from app.shared.config import get_settings
from app.shared.errors import TokenExpiredError, TokenInvalidError

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
