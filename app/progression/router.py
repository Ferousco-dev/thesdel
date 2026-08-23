from fastapi import APIRouter

from app.progression.schemas import BadgePublic, ProgressionMe, UserBadgePublic
from app.progression.service import ProgressionService
from app.shared.db import get_db
from app.shared.deps import CurrentUserDep

router = APIRouter(prefix="/v1/progression", tags=["progression"])

# No public "award me a badge" or "add my score" endpoint here by design —
# badges/score are awarded by other modules' business logic calling
# ProgressionService directly (server-side criteria evaluation), never by a
# client request. See docs/ARCHITECTURE.md §2 and this module's service.py.


def _service() -> ProgressionService:
    return ProgressionService(get_db())


@router.get("/me", response_model=ProgressionMe)
async def get_my_progression(user: CurrentUserDep) -> ProgressionMe:
    # Self-scoped: the current user is always resolved from the verified
    # JWT-authenticated dependency, never from a client-supplied user_id —
    # RULES.md #2.
    return await _service().get_summary(user_id=user.id)


@router.get("/badges", response_model=list[BadgePublic])
async def list_badge_catalog(user: CurrentUserDep) -> list[BadgePublic]:
    # Informational catalog, not self-scoped data — still requires auth so
    # it isn't a public unauthenticated endpoint.
    return await _service().list_badge_catalog()


@router.get("/badges/me", response_model=list[UserBadgePublic])
async def list_my_badges(user: CurrentUserDep) -> list[UserBadgePublic]:
    return await _service().list_badges_for_user(user_id=user.id)
