from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

# Pro-only, isolation-critical collection. Only this module's repository —
# and app/litheral/life (which is allowed to read routines per the Backend
# Spec's Pro scope) — may query it. app/litheral/study must NEVER import
# this file. See docs/DATABASE.md §1, RULES.md forbidden patterns.


class RoutineRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(self, *, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        doc = {"user_id": ObjectId(user_id), **fields}
        result = await self._db.routines.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, routine_id: str) -> dict[str, Any] | None:
        return await self._db.routines.find_one({"_id": ObjectId(routine_id)})

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self._db.routines.find({"user_id": ObjectId(user_id)})
        return [doc async for doc in cursor]

    async def update(self, routine_id: ObjectId, fields: dict[str, Any]) -> dict[str, Any] | None:
        await self._db.routines.update_one({"_id": routine_id}, {"$set": fields})
        return await self._db.routines.find_one({"_id": routine_id})

    async def delete(self, routine_id: ObjectId) -> None:
        await self._db.routines.delete_one({"_id": routine_id})
