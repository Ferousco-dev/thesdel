from fastapi import APIRouter, Depends, status

from app.litheral.study.schemas import (
    GenerateStudyPlanRequest,
    RegenerateBlockResponse,
    StudyBlockPublic,
)
from app.litheral.study.service import LitheralStudyService
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.deps import CurrentUser, require_tier
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/litheral/study", tags=["litheral-study"])

_require_premium = require_tier("premium")


def _service() -> LitheralStudyService:
    settings = get_settings()
    return LitheralStudyService(
        get_db(), get_redis(), regenerate_cap=settings.ai_cap_study_regenerate_monthly
    )


@router.post("/generate", response_model=list[StudyBlockPublic], status_code=status.HTTP_201_CREATED)
async def generate_study_plan(
    body: GenerateStudyPlanRequest,
    user: CurrentUser = Depends(_require_premium),
) -> list[StudyBlockPublic]:
    return await _service().generate(user_id=user.id, body=body)


@router.get("", response_model=list[StudyBlockPublic])
async def list_study_plan(
    user: CurrentUser = Depends(_require_premium),
) -> list[StudyBlockPublic]:
    return await _service().list_blocks(user_id=user.id)


@router.post("/{block_id}/regenerate", response_model=RegenerateBlockResponse)
async def regenerate_block(
    block_id: str,
    user: CurrentUser = Depends(_require_premium),
) -> RegenerateBlockResponse:
    return await _service().regenerate_block(user_id=user.id, block_id=block_id)
