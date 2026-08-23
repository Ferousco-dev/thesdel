from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._db.users.find_one({"email": email.lower()})

    async def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self._db.users.find_one({"_id": ObjectId(user_id)})

    async def find_by_google_id(self, google_id: str) -> dict[str, Any] | None:
        return await self._db.users.find_one({"google_id": google_id})

    async def create(
        self,
        *,
        email: str,
        display_name: str,
        password_hash: str | None = None,
        google_id: str | None = None,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        """`password_hash` is None for a Google-only account — there's no
        password to verify against, so `login()` must reject a password
        attempt for such an account rather than crash on a missing field."""
        doc: dict[str, Any] = {
            "email": email.lower(),
            "password_hash": password_hash,
            "email_verified_at": datetime.now(UTC) if email_verified else None,
            "display_name": display_name,
            "tier": "free",
            "tier_renewed_at": None,
            "theme_mode": "light",
            "theme_accent": None,
            "thesdel_score": 0,
            "rank": "unranked",
            "is_verified": False,
            "created_at": datetime.now(UTC),
        }
        # google_id is omitted entirely (not set to None) for password-only
        # accounts — the sparse unique index on users.google_id only
        # excludes documents where the field is absent, not documents where
        # it's explicitly null, so writing `None` here would collide once a
        # second password-only user registers.
        if google_id is not None:
            doc["google_id"] = google_id
        result = await self._db.users.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def link_google_id(self, user_id: ObjectId, google_id: str) -> None:
        await self._db.users.update_one({"_id": user_id}, {"$set": {"google_id": google_id}})

    async def mark_email_verified(self, user_id: str) -> None:
        await self._db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"email_verified_at": datetime.now(UTC)}},
        )

    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        await self._db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": password_hash}},
        )


class SessionRepository:
    """Refresh-token sessions. Tokens are stored hashed, never in plaintext —
    see docs/DECISIONS.md ADR-002 and docs/SECURITY.md §2."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        device_label: str | None,
        family_id: str,
    ) -> dict[str, Any]:
        doc = {
            "user_id": ObjectId(user_id),
            "refresh_token_hash": refresh_token_hash,
            "family_id": family_id,
            "device_label": device_label,
            "created_at": datetime.now(UTC),
            "expires_at": expires_at,
            "revoked_at": None,
        }
        result = await self._db.sessions.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_token_hash(self, refresh_token_hash: str) -> dict[str, Any] | None:
        return await self._db.sessions.find_one({"refresh_token_hash": refresh_token_hash})

    async def revoke(self, session_id: ObjectId) -> None:
        await self._db.sessions.update_one(
            {"_id": session_id}, {"$set": {"revoked_at": datetime.now(UTC)}}
        )

    async def revoke_family(self, family_id: str) -> None:
        """Reuse-detection response: a rotated-away refresh token being
        presented again signals theft — revoke the whole session family,
        not just the one token. See docs/SECURITY.md threat table."""
        await self._db.sessions.update_many(
            {"family_id": family_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )

    async def revoke_all_for_user(self, user_id: str) -> None:
        """A password reset must force re-login everywhere — revoke every
        active session for this user, not just one family."""
        await self._db.sessions.update_many(
            {"user_id": ObjectId(user_id), "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(UTC)}},
        )


class AuthTokenRepository:
    """Opaque, single-use tokens for email verification and password reset.
    Stored hashed at rest (never plaintext), short TTL, TTL-indexed for
    automatic cleanup. See docs/DATABASE.md `auth_tokens` and
    docs/DECISIONS.md ADR-010."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(
        self, *, user_id: str, purpose: str, token_hash: str, expires_at: datetime
    ) -> dict[str, Any]:
        # Invalidate any earlier outstanding token of the same purpose for
        # this user, so only the most recently issued one is usable.
        await self._db.auth_tokens.update_many(
            {"user_id": ObjectId(user_id), "purpose": purpose, "used_at": None},
            {"$set": {"used_at": datetime.now(UTC)}},
        )
        doc = {
            "user_id": ObjectId(user_id),
            "purpose": purpose,
            "token_hash": token_hash,
            "created_at": datetime.now(UTC),
            "expires_at": expires_at,
            "used_at": None,
            "sent_at": None,
        }
        result = await self._db.auth_tokens.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_hash(self, token_hash: str) -> dict[str, Any] | None:
        return await self._db.auth_tokens.find_one({"token_hash": token_hash})

    async def mark_sent(self, token_id: ObjectId) -> None:
        await self._db.auth_tokens.update_one(
            {"_id": token_id}, {"$set": {"sent_at": datetime.now(UTC)}}
        )

    async def mark_used(self, token_id: ObjectId) -> None:
        await self._db.auth_tokens.update_one(
            {"_id": token_id}, {"$set": {"used_at": datetime.now(UTC)}}
        )
