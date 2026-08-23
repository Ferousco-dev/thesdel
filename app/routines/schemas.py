from pydantic import BaseModel, Field

RoutineLabel = str  # "Church" | "Gym" | "Work" | "Sleep" | "Meals" | "Personal"

_ALLOWED_LABELS = {"Church", "Gym", "Work", "Sleep", "Meals", "Personal"}


class RoutineCreate(BaseModel):
    label: str
    days: list[int] = Field(min_length=1)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    is_flexible: bool = False

    def model_post_init(self, __context) -> None:
        if self.label not in _ALLOWED_LABELS:
            raise ValueError(f"label must be one of {sorted(_ALLOWED_LABELS)}")
        if any(d < 0 or d > 6 for d in self.days):
            raise ValueError("days must be 0-6")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")


class RoutineUpdate(BaseModel):
    label: str | None = None
    days: list[int] | None = None
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    is_flexible: bool | None = None


class RoutinePublic(BaseModel):
    id: str
    label: str
    days: list[int]
    start_time: str
    end_time: str
    is_flexible: bool
