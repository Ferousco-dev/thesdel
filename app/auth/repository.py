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

    async def create(self, *, email: str, password_hash: str, display_name: str) -> dict[str, Any]:
        doc = {
            "email": email.lower(),
            "password_hash": password_hash,
            "email_verified_at": None,
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
        result = await self._db.users.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc


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
