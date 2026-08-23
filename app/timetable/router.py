from fastapi import APIRouter, status

from app.shared.db import get_db
from app.shared.deps import ClassMembershipDep, ClassRepDep, CurrentUserDep
from app.timetable.schemas import TimetableEntryCreate, TimetableEntryPublic, TimetableEntryUpdate
from app.timetable.service import TimetableService

router = APIRouter(prefix="/v1", tags=["timetable"])


def _service() -> TimetableService:
    return TimetableService(get_db())


@router.get("/timetable", response_model=list[TimetableEntryPublic])
async def list_my_timetable(user: CurrentUserDep) -> list[TimetableEntryPublic]:
    return await _service().list_personal(user_id=user.id)


@router.post("/timetable", response_model=TimetableEntryPublic, status_code=status.HTTP_201_CREATED)
async def create_my_timetable_entry(
    body: TimetableEntryCreate, user: CurrentUserDep
) -> TimetableEntryPublic:
    return await _service().create_personal_entry(user_id=user.id, body=body)


@router.patch("/timetable/{entry_id}", response_model=TimetableEntryPublic)
async def update_my_timetable_entry(
    entry_id: str, body: TimetableEntryUpdate, user: CurrentUserDep
) -> TimetableEntryPublic:
    return await _service().update_personal_entry(user_id=user.id, entry_id=entry_id, body=body)


@router.delete("/timetable/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_timetable_entry(entry_id: str, user: CurrentUserDep) -> None:
    await _service().delete_personal_entry(user_id=user.id, entry_id=entry_id)


@router.get("/timetable/class/{class_id}", response_model=list[TimetableEntryPublic])
async def list_class_timetable(
    class_id: str, membership: ClassMembershipDep
) -> list[TimetableEntryPublic]:
    return await _service().list_class(class_id=class_id)


@router.post(
    "/timetable/class/{class_id}",
    response_model=TimetableEntryPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_class_timetable_entry(
    class_id: str, body: TimetableEntryCreate, rep: ClassRepDep
) -> TimetableEntryPublic:
    return await _service().create_class_entry(class_id=class_id, body=body)
