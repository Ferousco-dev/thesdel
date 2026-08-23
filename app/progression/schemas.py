from datetime import date, datetime

from pydantic import BaseModel


class BadgePublic(BaseModel):
    id: str
    family: str
    name: str
    criteria_type: str
    criteria_value: object


class UserBadgePublic(BaseModel):
    badge_id: str
    family: str
    name: str
    earned_at: datetime


class SeasonPublic(BaseModel):
    id: str
    start_date: date
    end_date: date


class ProgressionMe(BaseModel):
    thesdel_score: int
    rank: str
    current_season: SeasonPublic | None
