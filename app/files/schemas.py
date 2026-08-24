from datetime import datetime

from pydantic import BaseModel


class FileUploadPublic(BaseModel):
    id: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime


class FileDownloadUrl(BaseModel):
    file_id: str
    url: str
    expires_in_seconds: int
