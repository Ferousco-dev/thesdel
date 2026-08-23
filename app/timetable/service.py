from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.shared.errors import NotFoundError
from app.timetable.repository import TimetableRepository
from app.timetable.schemas import TimetableEntryCreate, TimetableEntryPublic, TimetableEntryUpdate


class TimetableService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = TimetableRepository(db)

    async def create_personal_entry(
        self, *, user_id: str, body: TimetableEntryCreate
    ) -> TimetableEntryPublic:
        doc = await self._repo.create(
            owner_type="user",
            owner_id=ObjectId(user_id),
            fields=body.model_dump(),
        )
        return _to_public(doc)

    async def create_class_entry(
        self, *, class_id: str, body: TimetableEntryCreate
    ) -> TimetableEntryPublic:
        doc = await self._repo.create(
            owner_type="class",
            owner_id=ObjectId(class_id),
            fields=body.model_dump(),
        )
        return _to_public(doc)

    async def list_personal(self, *, user_id: str) -> list[TimetableEntryPublic]:
        docs = await self._repo.list_for_owner(owner_type="user", owner_id=ObjectId(user_id))
        return [_to_public(doc) for doc in docs]

    async def list_class(self, *, class_id: str) -> list[TimetableEntryPublic]:
        docs = await self._repo.list_for_owner(owner_type="class", owner_id=ObjectId(class_id))
        return [_to_public(doc) for doc in docs]

    async def update_personal_entry(
        self, *, user_id: str, entry_id: str, body: TimetableEntryUpdate
    ) -> TimetableEntryPublic:
        existing = await self._require_owned_by_user(entry_id=entry_id, user_id=user_id)
        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
        updated = await self._repo.update(existing["_id"], fields)
        return _to_public(updated)

    async def delete_personal_entry(self, *, user_id: str, entry_id: str) -> None:
        existing = await self._require_owned_by_user(entry_id=entry_id, user_id=user_id)
        await self._repo.delete(existing["_id"])

    async def _require_owned_by_user(self, *, entry_id: str, user_id: str) -> dict:
        doc = await self._repo.find_by_id(entry_id)
        if doc is None:
            raise NotFoundError()
        if doc["owner_type"] != "user" or str(doc["owner_id"]) != user_id:
            # 404, not 403 — do not confirm existence of another user's
            # entry, per docs/SECURITY.md §4 IDOR guidance.
            raise NotFoundError()
        return doc


def _to_public(doc: dict) -> TimetableEntryPublic:
    return TimetableEntryPublic(
        id=str(doc["_id"]),
        owner_type=doc["owner_type"],
        owner_id=str(doc["owner_id"]),
        subject=doc["subject"],
        day_of_week=doc["day_of_week"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        location=doc.get("location"),
        recurrence=doc.get("recurrence"),
    )
