from fastapi import APIRouter, Depends, status

from app.litheral.life.schemas import LifeBlockPublic
from app.litheral.life.service import LitheralLifeService
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.deps import CurrentUser, require_tier
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/litheral/life", tags=["litheral-life"])

_require_pro = require_tier("pro")


def _service() -> LitheralLifeService:
    settings = get_settings()
    return LitheralLifeService(get_db(), get_redis(), adjust_cap=settings.ai_cap_life_adjust_monthly)


@router.post("/generate", response_model=list[LifeBlockPublic], status_code=status.HTTP_201_CREATED)
async def generate_life_schedule(
    user: CurrentUser = Depends(_require_pro),
) -> list[LifeBlockPublic]:
    return await _service().generate(user_id=user.id)


@router.get("", response_model=list[LifeBlockPublic])
async def list_life_schedule(user: CurrentUser = Depends(_require_pro)) -> list[LifeBlockPublic]:
    return await _service().list_blocks(user_id=user.id)


@router.post("/adjust", response_model=list[LifeBlockPublic])
async def adjust_life_schedule(user: CurrentUser = Depends(_require_pro)) -> list[LifeBlockPublic]:
    return await _service().adjust(user_id=user.id)
