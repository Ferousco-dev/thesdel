from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class LifeScheduleRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def replace_all_for_user(
        self, *, user_id: str, blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        user_oid = ObjectId(user_id)
        await self._db.life_schedule_blocks.delete_many({"user_id": user_oid})
        if not blocks:
            return []
        docs = [{"user_id": user_oid, **b, "generated_at": datetime.now(UTC)} for b in blocks]
        result = await self._db.life_schedule_blocks.insert_many(docs)
        for doc, inserted_id in zip(docs, result.inserted_ids, strict=True):
            doc["_id"] = inserted_id
        return docs

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self._db.life_schedule_blocks.find({"user_id": ObjectId(user_id)}).sort(
            [("day_of_week", 1), ("start_time", 1)]
        )
        return [doc async for doc in cursor]
