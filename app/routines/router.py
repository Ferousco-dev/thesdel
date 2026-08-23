from fastapi import APIRouter, Depends, status

from app.routines.schemas import RoutineCreate, RoutinePublic, RoutineUpdate
from app.routines.service import RoutineService
from app.shared.db import get_db
from app.shared.deps import CurrentUser, require_tier

router = APIRouter(prefix="/v1/litheral/routines", tags=["routines"])

_require_pro = require_tier("pro")


def _service() -> RoutineService:
    return RoutineService(get_db())


@router.post("", response_model=RoutinePublic, status_code=status.HTTP_201_CREATED)
async def create_routine(
    body: RoutineCreate, user: CurrentUser = Depends(_require_pro)
) -> RoutinePublic:
    return await _service().create(user_id=user.id, body=body)


@router.get("", response_model=list[RoutinePublic])
async def list_routines(user: CurrentUser = Depends(_require_pro)) -> list[RoutinePublic]:
    return await _service().list_for_user(user_id=user.id)


@router.patch("/{routine_id}", response_model=RoutinePublic)
async def update_routine(
    routine_id: str, body: RoutineUpdate, user: CurrentUser = Depends(_require_pro)
) -> RoutinePublic:
    return await _service().update(user_id=user.id, routine_id=routine_id, body=body)


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routine(routine_id: str, user: CurrentUser = Depends(_require_pro)) -> None:
    await _service().delete(user_id=user.id, routine_id=routine_id)
