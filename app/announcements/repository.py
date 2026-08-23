from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class AnnouncementRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(self, *, class_id: ObjectId, posted_by: ObjectId, content: str) -> dict[str, Any]:
        doc = {
            "class_id": class_id,
            "posted_by": posted_by,
            "content": content,
            "pinned": False,
            "created_at": datetime.now(UTC),
        }
        result = await self._db.announcements.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, announcement_id: str) -> dict[str, Any] | None:
        return await self._db.announcements.find_one({"_id": ObjectId(announcement_id)})

    async def list_pinned(self, class_id: ObjectId) -> list[dict[str, Any]]:
        # Pinned volume is expected to be small (rep-curated), so this is
        # not paginated — serves the "pinned at top" requirement directly.
        # See docs/DATABASE.md §1 (announcements index).
        cursor = self._db.announcements.find(
            {"class_id": class_id, "pinned": True}
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def list_unpinned_page(
        self, class_id: ObjectId, *, before: tuple[datetime, ObjectId] | None, limit: int
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"class_id": class_id, "pinned": False}
        if before is not None:
            created_at, obj_id = before
            query["$or"] = [
                {"created_at": {"$lt": created_at}},
                {"created_at": created_at, "_id": {"$lt": obj_id}},
            ]
        cursor = (
            self._db.announcements.find(query)
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )
        return [doc async for doc in cursor]

    async def update(self, announcement_id: ObjectId, fields: dict[str, Any]) -> dict[str, Any] | None:
        await self._db.announcements.update_one({"_id": announcement_id}, {"$set": fields})
        return await self._db.announcements.find_one({"_id": announcement_id})
