from fastapi import APIRouter, status

from app.classes.schemas import (
    ClassPreview,
    ClassPublic,
    ClassPublicWithRole,
    CreateClassRequest,
    JoinClassRequest,
    MembershipPublic,
)
from app.classes.service import ClassService
from app.shared.db import get_db
from app.shared.deps import ClassMembershipDep, CurrentUserDep

router = APIRouter(prefix="/v1/classes", tags=["classes"])


def _service() -> ClassService:
    return ClassService(get_db())


@router.post("", response_model=ClassPublic, status_code=status.HTTP_201_CREATED)
async def create_class(body: CreateClassRequest, user: CurrentUserDep) -> ClassPublic:
    return await _service().create_class(name=body.name, created_by=user.id)


@router.get("/preview", response_model=ClassPreview)
async def preview_class(join_code: str, user: CurrentUserDep) -> ClassPreview:
    return await _service().preview_by_join_code(join_code)


@router.post("/join", response_model=MembershipPublic)
async def join_class(body: JoinClassRequest, user: CurrentUserDep) -> MembershipPublic:
    return await _service().join_class(join_code=body.join_code, user_id=user.id)


@router.get("", response_model=list[ClassPublicWithRole])
async def list_my_classes(user: CurrentUserDep) -> list[ClassPublicWithRole]:
    return await _service().list_my_classes(user.id)


@router.get("/{class_id}", response_model=ClassPublic)
async def get_class(class_id: str, membership: ClassMembershipDep) -> ClassPublic:
    # membership dependency already verified the caller belongs to this
    # class — 404 if not, without revealing whether the class exists.
    return await _service().get_class(class_id)
