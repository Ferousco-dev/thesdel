from fastapi import APIRouter, status

from app.shared.db import get_db
from app.shared.deps import CurrentUserDep
from app.streaks.schemas import (
    CheckInResult,
    StreakAcceptRequest,
    StreakCheckInRequest,
    StreakInviteRequest,
    StreakPublic,
)
from app.streaks.service import StreakService

router = APIRouter(prefix="/v1/streaks", tags=["streaks"])


def _service() -> StreakService:
    return StreakService(get_db())


@router.post("/invite", response_model=StreakPublic, status_code=status.HTTP_201_CREATED)
async def invite_streak(body: StreakInviteRequest, user: CurrentUserDep) -> StreakPublic:
    return await _service().invite(current_user_id=user.id, invitee_user_id=body.invitee_user_id)


@router.post("/accept", response_model=StreakPublic)
async def accept_streak(body: StreakAcceptRequest, user: CurrentUserDep) -> StreakPublic:
    return await _service().accept(current_user_id=user.id, inviter_user_id=body.inviter_user_id)


@router.post("/check-in", response_model=CheckInResult)
async def check_in(body: StreakCheckInRequest, user: CurrentUserDep) -> CheckInResult:
    return await _service().check_in(current_user_id=user.id, partner_user_id=body.partner_user_id)


@router.get("/me", response_model=list[StreakPublic])
async def list_my_streaks(user: CurrentUserDep) -> list[StreakPublic]:
    return await _service().list_my_streaks(current_user_id=user.id)


@router.get("/{partner_user_id}", response_model=StreakPublic)
async def get_streak_with_partner(partner_user_id: str, user: CurrentUserDep) -> StreakPublic:
    return await _service().get_with_partner(
        current_user_id=user.id, partner_user_id=partner_user_id
    )
