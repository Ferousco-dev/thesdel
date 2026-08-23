from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class AnnouncementUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=2000)
    pinned: bool | None = None


class AnnouncementPublic(BaseModel):
    id: str
    class_id: str
    posted_by: str
    content: str
    pinned: bool
    created_at: datetime


class AnnouncementPage(BaseModel):
    items: list[AnnouncementPublic]
    next_cursor: str | None
