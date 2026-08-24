"""Raw Mongo access for `file_uploads`. See docs/DATABASE.md's `file_uploads`
section for the collection shape and index rationale.
"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

# A user's pending-upload count is inherently small (they upload one
# timetable image, wait for parsing, repeat) — bounded defensively per
# RULES.md #6, not because it's expected to be hit.
_STALE_SWEEP_HARD_CAP = 500


class FileUploadRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(
        self,
        *,
        user_id: ObjectId,
        r2_key: str,
        content_type: str,
        size_bytes: int,
        created_at: datetime,
    ) -> dict[str, Any]:
        doc = {
            "user_id": user_id,
            "r2_key": r2_key,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "status": "pending_parse",
            "created_at": created_at,
        }
        result = await self._db.file_uploads.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_owned(self, *, file_id: ObjectId, user_id: ObjectId) -> dict[str, Any] | None:
        """Ownership is re-verified in the query itself, per RULES.md #4 —
        an existing `_id` alone is never authorization."""
        return await self._db.file_uploads.find_one({"_id": file_id, "user_id": user_id})

    async def delete_owned(self, *, file_id: ObjectId, user_id: ObjectId) -> dict[str, Any] | None:
        return await self._db.file_uploads.find_one_and_delete(
            {"_id": file_id, "user_id": user_id}
        )

    async def find_stale_pending(
        self, *, older_than: datetime, limit: int = _STALE_SWEEP_HARD_CAP
    ) -> list[dict[str, Any]]:
        """Serves the abandoned-upload cleanup sweep (app/files/jobs.py):
        `pending_parse` records whose `created_at` is older than the bounded
        TTL. See docs/DATABASE.md query-pattern table for the backing
        `{status, created_at}` index."""
        cursor = self._db.file_uploads.find(
            {"status": "pending_parse", "created_at": {"$lt": older_than}}
        ).limit(min(limit, _STALE_SWEEP_HARD_CAP))
        return [doc async for doc in cursor]

    async def delete_by_id(self, file_id: ObjectId) -> None:
        await self._db.file_uploads.delete_one({"_id": file_id})
