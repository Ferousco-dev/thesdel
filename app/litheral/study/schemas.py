from datetime import date, datetime

from pydantic import BaseModel, Field


class SubjectInputModel(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    priority: int | None = Field(default=None, ge=1, le=5)
    exam_date: date | None = None


class GenerateStudyPlanRequest(BaseModel):
    subjects: list[SubjectInputModel] = Field(default_factory=list, max_length=30)


class StudyBlockPublic(BaseModel):
    id: str
    subject: str
    priority: int | None
    exam_date: date | None
    day_of_week: int
    start_time: str
    end_time: str
    generated_at: datetime


class RegenerateBlockResponse(BaseModel):
    block: StudyBlockPublic
    remaining_regenerations: int
