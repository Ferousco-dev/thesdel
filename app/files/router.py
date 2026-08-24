"""Upload/retrieve/delete endpoints for timetable-import images.

Scope: upload -> validate -> store -> retrieve/delete only. This module
deliberately does NOT call an LLM to parse the stored image into
timetable_entries — see the service module's docstring and
docs/DECISIONS.md ADR-014 for why that's a scope decision, not an
oversight. An uploaded file simply lands in `pending_parse` status.
"""

from fastapi import APIRouter, UploadFile, status

from app.files.schemas import FileDownloadUrl, FileUploadPublic
from app.files.service import MAX_UPLOAD_BYTES, FileService
from app.shared.db import get_db
from app.shared.deps import CurrentUserDep
from app.shared.errors import ValidationAppError

router = APIRouter(prefix="/v1/files", tags=["files"])


def _service() -> FileService:
    return FileService(get_db())


@router.post(
    "/timetable-import",
    response_model=FileUploadPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_timetable_import(file: UploadFile, user: CurrentUserDep) -> FileUploadPublic:
    # Read up to the cap + 1 byte so an oversized upload is rejected
    # without buffering the whole (potentially huge) body first —
    # docs/SECURITY.md's file-upload threat row ("size cap enforced before
    # fully buffering if reasonably possible").
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise ValidationAppError("File is too large.")
        chunks.append(chunk)
    raw_bytes = b"".join(chunks)

    # Self-scoped: user_id always comes from the verified current-user
    # dependency, never from the request — RULES.md #2.
    return await _service().upload_timetable_import(user_id=user.id, raw_bytes=raw_bytes)


@router.get("/timetable-import/{file_id}", response_model=FileDownloadUrl)
async def get_timetable_import_url(file_id: str, user: CurrentUserDep) -> FileDownloadUrl:
    return await _service().get_download_url(user_id=user.id, file_id=file_id)


@router.delete("/timetable-import/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timetable_import(file_id: str, user: CurrentUserDep) -> None:
    await _service().delete(user_id=user.id, file_id=file_id)
