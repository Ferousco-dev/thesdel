from datetime import datetime

from pydantic import BaseModel


class FeatureCapStatus(BaseModel):
    feature: str
    used: int
    limit: int
    remaining: int
    resets_at: datetime


class UsageStatusResponse(BaseModel):
    caps: list[FeatureCapStatus]
