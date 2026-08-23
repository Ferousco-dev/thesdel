from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class TimetableRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(self, *, owner_type: str, owner_id: ObjectId, fields: dict[str, Any]) -> dict[str, Any]:
        doc = {"owner_type": owner_type, "owner_id": owner_id, **fields}
        result = await self._db.timetable_entries.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, entry_id: str) -> dict[str, Any] | None:
        return await self._db.timetable_entries.find_one({"_id": ObjectId(entry_id)})

    async def list_for_owner(self, *, owner_type: str, owner_id: ObjectId) -> list[dict[str, Any]]:
        cursor = self._db.timetable_entries.find(
            {"owner_type": owner_type, "owner_id": owner_id}
        ).sort([("day_of_week", 1), ("start_time", 1)])
        return [doc async for doc in cursor]

    async def update(self, entry_id: ObjectId, fields: dict[str, Any]) -> dict[str, Any] | None:
        await self._db.timetable_entries.update_one({"_id": entry_id}, {"$set": fields})
        return await self._db.timetable_entries.find_one({"_id": entry_id})

    async def delete(self, entry_id: ObjectId) -> None:
        await self._db.timetable_entries.delete_one({"_id": entry_id})
