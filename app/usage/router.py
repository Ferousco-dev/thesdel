from fastapi import APIRouter

from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.deps import CurrentUserDep
from app.shared.redis_client import get_redis
from app.usage.schemas import FeatureCapStatus, UsageStatusResponse
from app.usage.service import AiUsageService

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/ai", response_model=UsageStatusResponse)
async def get_ai_usage(user: CurrentUserDep) -> UsageStatusResponse:
    settings = get_settings()
    service = AiUsageService(get_db(), get_redis())

    features = [
        ("study_regenerate", settings.ai_cap_study_regenerate_monthly),
        ("life_adjust", settings.ai_cap_life_adjust_monthly),
    ]

    caps = []
    for feature, limit in features:
        status = await service.get_status(user_id=user.id, feature=feature, limit=limit)
        caps.append(
            FeatureCapStatus(
                feature=feature,
                used=status.used,
                limit=status.limit,
                remaining=max(0, status.limit - status.used),
                resets_at=status.resets_at,
            )
        )

    return UsageStatusResponse(caps=caps)
