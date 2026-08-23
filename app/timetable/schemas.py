from pydantic import BaseModel, Field, field_validator


class TimetableEntryCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    location: str | None = Field(default=None, max_length=120)
    recurrence: str | None = Field(default=None, max_length=40)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: str, info) -> str:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class TimetableEntryUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    location: str | None = None
    recurrence: str | None = None


class TimetableEntryPublic(BaseModel):
    id: str
    owner_type: str
    owner_id: str
    subject: str
    day_of_week: int
    start_time: str
    end_time: str
    location: str | None
    recurrence: str | None
