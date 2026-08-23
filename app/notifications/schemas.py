from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["ios", "android", "web"]


class DeviceTokenRegister(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
    platform: Platform


class DeviceTokenPublic(BaseModel):
    id: str
    platform: Platform
    created_at: datetime
    last_seen_at: datetime
