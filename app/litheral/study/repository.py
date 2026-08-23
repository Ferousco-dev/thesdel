from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

# Isolation rule (spec-mandated, see docs/DATABASE.md §1 "study_plans" and
# RULES.md forbidden patterns): only this module's repository may query
# study_plans, and this module must never import routines/'s repository.


class StudyPlanRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def replace_all_for_user(self, *, user_id: str, blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        user_oid = ObjectId(user_id)
        await self._db.study_plans.delete_many({"user_id": user_oid})
        if not blocks:
            return []
        docs = [{"user_id": user_oid, **block, "generated_at": datetime.now(UTC)} for block in blocks]
        result = await self._db.study_plans.insert_many(docs)
        for doc, inserted_id in zip(docs, result.inserted_ids, strict=True):
            doc["_id"] = inserted_id
        return docs

    async def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self._db.study_plans.find({"user_id": ObjectId(user_id)}).sort(
            [("day_of_week", 1), ("start_time", 1)]
        )
        return [doc async for doc in cursor]

    async def find_by_id(self, block_id: str) -> dict[str, Any] | None:
        return await self._db.study_plans.find_one({"_id": ObjectId(block_id)})

    async def replace_block(self, block_id: ObjectId, fields: dict[str, Any]) -> dict[str, Any] | None:
        await self._db.study_plans.update_one(
            {"_id": block_id}, {"$set": {**fields, "generated_at": datetime.now(UTC)}}
        )
        return await self._db.study_plans.find_one({"_id": block_id})
