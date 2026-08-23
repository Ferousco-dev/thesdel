from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase


class ClassRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def create(self, *, name: str, created_by: str, join_code: str) -> dict[str, Any]:
        doc = {
            "name": name,
            "created_by": ObjectId(created_by),
            "join_code": join_code,
            "member_count": 1,
            "created_at": datetime.now(UTC),
        }
        result = await self._db.classes.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_id(self, class_id: str) -> dict[str, Any] | None:
        return await self._db.classes.find_one({"_id": ObjectId(class_id)})

    async def find_by_join_code(self, join_code: str) -> dict[str, Any] | None:
        return await self._db.classes.find_one({"join_code": join_code})

    async def increment_member_count(
        self, class_id: ObjectId, *, session: AsyncIOMotorClientSession | None = None
    ) -> None:
        # Denormalized counter, incremented atomically here — never
        # recomputed live. See docs/DATABASE.md §1 (classes.member_count).
        await self._db.classes.update_one(
            {"_id": class_id}, {"$inc": {"member_count": 1}}, session=session
        )


class ClassMemberRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find(self, class_id: ObjectId, user_id: ObjectId) -> dict[str, Any] | None:
        return await self._db.class_members.find_one({"class_id": class_id, "user_id": user_id})

    async def add(
        self,
        *,
        class_id: ObjectId,
        user_id: ObjectId,
        role: str,
        session: AsyncIOMotorClientSession | None = None,
    ) -> dict[str, Any]:
        doc = {
            "class_id": class_id,
            "user_id": user_id,
            "role": role,
            "joined_at": datetime.now(UTC),
        }
        await self._db.class_members.insert_one(doc, session=session)
        return doc

    async def list_class_ids_for_user(self, user_id: ObjectId) -> list[ObjectId]:
        cursor = self._db.class_members.find({"user_id": user_id}, {"class_id": 1})
        return [doc["class_id"] async for doc in cursor]

    async def list_user_ids_for_class(self, class_id: ObjectId) -> list[ObjectId]:
        # Bounded by the existing {class_id, user_id} index (see
        # docs/DATABASE.md §1) — used by ClassService.list_member_user_ids
        # to build the announcement-push fan-out list.
        cursor = self._db.class_members.find({"class_id": class_id}, {"user_id": 1})
        return [doc["user_id"] async for doc in cursor]
