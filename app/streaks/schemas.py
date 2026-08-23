from datetime import datetime

from pydantic import BaseModel, Field


class StreakInviteRequest(BaseModel):
    invitee_user_id: str = Field(min_length=1, max_length=64)


class StreakAcceptRequest(BaseModel):
    inviter_user_id: str = Field(min_length=1, max_length=64)


class StreakCheckInRequest(BaseModel):
    partner_user_id: str = Field(min_length=1, max_length=64)


class StreakPublic(BaseModel):
    id: str
    user_a: str
    user_b: str
    current_streak: int
    last_interaction_at: datetime | None
    status: str


class CheckInResult(BaseModel):
    streak: StreakPublic
    already_checked_in_today: bool
