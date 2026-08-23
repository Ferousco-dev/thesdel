from datetime import datetime

from pydantic import BaseModel


class LifeBlockPublic(BaseModel):
    id: str
    source_type: str
    source_id: str
    day_of_week: int
    start_time: str
    end_time: str
    conflict_flag: bool
    generated_at: datetime
