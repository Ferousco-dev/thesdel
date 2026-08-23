from fastapi import APIRouter

from app.auth.schemas import UserPublic
from app.shared.deps import CurrentUserDep

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUserDep) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name, tier=user.tier)
