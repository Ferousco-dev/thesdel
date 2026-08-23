from fastapi import APIRouter, status

from app.notifications.schemas import DeviceTokenPublic, DeviceTokenRegister
from app.notifications.service import NotificationService
from app.shared.db import get_db
from app.shared.deps import CurrentUserDep
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


def _service() -> NotificationService:
    return NotificationService(get_db(), get_redis())


@router.post("/devices", response_model=DeviceTokenPublic, status_code=status.HTTP_201_CREATED)
async def register_device(body: DeviceTokenRegister, user: CurrentUserDep) -> DeviceTokenPublic:
    # Self-scoped: user_id always comes from the verified current-user
    # dependency, never from the request body — RULES.md #2.
    return await _service().register_device(
        user_id=user.id, token=body.token, platform=body.platform
    )


@router.delete("/devices/{token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(token: str, user: CurrentUserDep) -> None:
    await _service().unregister_device(user_id=user.id, token=token)
