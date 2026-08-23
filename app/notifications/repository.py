"""Raw Mongo access for `device_tokens`. See docs/DATABASE.md's
`device_tokens` section for the collection design and index rationale."""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class DeviceTokenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def upsert(self, *, user_id: ObjectId, token: str, platform: str) -> dict[str, Any]:
        """Registering an already-known token for the same user is
        idempotent — a device re-registering its token on every app launch
        is the expected steady-state traffic pattern (per task spec), so
        this is an upsert keyed on the unique `token` value, not an insert.
        """
        now = datetime.now(UTC)
        doc = await self._db.device_tokens.find_one_and_update(
            {"token": token},
            {
                "$set": {
                    "user_id": user_id,
                    "platform": platform,
                    "last_seen_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        return doc

    async def delete(self, *, user_id: ObjectId, token: str) -> bool:
        """Deletes a token, scoped to the owning user — a user can never
        unregister another user's token (RULES.md #2/#4)."""
        result = await self._db.device_tokens.delete_one({"user_id": user_id, "token": token})
        return result.deleted_count > 0

    async def delete_by_token(self, token: str) -> None:
        """Prunes a dead/invalid token reported by FCM — not scoped to a
        user since the job path already resolved it by token, not by
        client-supplied user ownership."""
        await self._db.device_tokens.delete_one({"token": token})

    async def list_tokens_for_user(self, user_id: ObjectId) -> list[str]:
        cursor = self._db.device_tokens.find({"user_id": user_id}, {"token": 1})
        return [doc["token"] async for doc in cursor]
