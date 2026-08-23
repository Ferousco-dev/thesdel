from fastapi import APIRouter, Query, status

from app.announcements.schemas import AnnouncementCreate, AnnouncementPage, AnnouncementPublic, AnnouncementUpdate
from app.announcements.service import AnnouncementService
from app.shared.config import get_settings
from app.shared.db import get_db
from app.shared.deps import ClassMembershipDep, ClassRepDep
from app.shared.rate_limit import check_rate_limit
from app.shared.redis_client import get_redis

router = APIRouter(prefix="/v1/classes/{class_id}/announcements", tags=["announcements"])


def _service() -> AnnouncementService:
    return AnnouncementService(get_db(), get_redis())


@router.get("", response_model=AnnouncementPage)
async def list_announcements(
    class_id: str,
    membership: ClassMembershipDep,
    cursor: str | None = Query(default=None),
) -> AnnouncementPage:
    return await _service().list_feed(class_id=class_id, cursor=cursor)


@router.post("", response_model=AnnouncementPublic, status_code=status.HTTP_201_CREATED)
async def post_announcement(
    class_id: str, body: AnnouncementCreate, rep: ClassRepDep
) -> AnnouncementPublic:
    settings = get_settings()
    await check_rate_limit(
        get_redis(),
        key=f"ratelimit:announcements:post:{rep.user_id}",
        max_requests=settings.rate_limit_default_max,
        window_seconds=settings.rate_limit_default_window_seconds,
        fail_closed=True,
    )
    return await _service().post(class_id=class_id, posted_by=rep.user_id, body=body)


@router.patch("/{announcement_id}", response_model=AnnouncementPublic)
async def update_announcement(
    class_id: str, announcement_id: str, body: AnnouncementUpdate, rep: ClassRepDep
) -> AnnouncementPublic:
    return await _service().update(
        announcement_id=announcement_id, content=body.content, pinned=body.pinned
    )
