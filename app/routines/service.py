from motor.motor_asyncio import AsyncIOMotorDatabase

from app.routines.repository import RoutineRepository
from app.routines.schemas import RoutineCreate, RoutinePublic, RoutineUpdate
from app.shared.errors import NotFoundError


class RoutineService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = RoutineRepository(db)

    async def create(self, *, user_id: str, body: RoutineCreate) -> RoutinePublic:
        doc = await self._repo.create(user_id=user_id, fields=body.model_dump())
        return _to_public(doc)

    async def list_for_user(self, *, user_id: str) -> list[RoutinePublic]:
        docs = await self._repo.list_for_user(user_id)
        return [_to_public(doc) for doc in docs]

    async def update(self, *, user_id: str, routine_id: str, body: RoutineUpdate) -> RoutinePublic:
        doc = await self._require_owned(user_id=user_id, routine_id=routine_id)
        fields = body.model_dump(exclude_unset=True)
        updated = await self._repo.update(doc["_id"], fields)
        return _to_public(updated)

    async def delete(self, *, user_id: str, routine_id: str) -> None:
        doc = await self._require_owned(user_id=user_id, routine_id=routine_id)
        await self._repo.delete(doc["_id"])

    async def _require_owned(self, *, user_id: str, routine_id: str) -> dict:
        doc = await self._repo.find_by_id(routine_id)
        if doc is None or str(doc["user_id"]) != user_id:
            raise NotFoundError()
        return doc


def _to_public(doc: dict) -> RoutinePublic:
    return RoutinePublic(
        id=str(doc["_id"]),
        label=doc["label"],
        days=doc["days"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        is_flexible=doc["is_flexible"],
    )
