"""Business logic for timetable-import file uploads.

Scope boundary (see docs/DECISIONS.md ADR-014 and the module docstring in
app/files/router.py): this module owns upload/validate/store/retrieve/
delete of the raw image only. It does NOT call any LLM to parse the image
into timetable_entries — no LLM provider has been selected anywhere in
this repo (docs/RESEARCH.md #2 names no provider; `llm_api_key` in
app/shared/config.py is an unused placeholder). A stored upload just sits
in `pending_parse` status until some future, separately-scoped change adds
the parsing step.
"""

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image, UnidentifiedImageError

from app.files.repository import FileUploadRepository
from app.files.schemas import FileDownloadUrl, FileUploadPublic
from app.shared.errors import NotFoundError, ValidationAppError
from app.shared.storage import ObjectNotFoundError, StorageClient, get_storage_client

# Allow-list: the three formats the frontend timetable-import screen is
# expected to produce (photo/screenshot of a printed or digital
# timetable). See docs/ARCHITECTURE.md §10 and docs/SECURITY.md's
# file-upload threat row.
_ALLOWED_FORMATS: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_EXTENSION_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

# Size cap enforced on the raw upload before it's fully buffered (read in
# chunks, abort as soon as this is exceeded) — 8 MiB comfortably covers a
# phone photo of a timetable without inviting abuse.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Decompression-bomb guard: cap max pixel dimensions independent of
# Pillow's default `Image.MAX_IMAGE_PIXELS` (~89M px) — bounded low enough
# that a legitimate timetable photo/screenshot is never rejected, but a
# crafted huge-dimension file is, before it's ever fully decoded.
_MAX_PIXEL_DIMENSION = 6000
_MAX_TOTAL_PIXELS = _MAX_PIXEL_DIMENSION * _MAX_PIXEL_DIMENSION

# Presigned GET URL expiry — short-lived per docs/ARCHITECTURE.md §10
# ("access is via short-lived signed URLs"). 10 minutes: long enough for a
# client to fetch the image once render-side, short enough that a leaked
# URL (e.g. via referrer, logs) is worthless shortly after. See
# docs/DECISIONS.md ADR-014.
PRESIGN_EXPIRY_SECONDS = 10 * 60

# Bounded TTL for abandoned pending_parse uploads (docs/PRIVACY.md §3) —
# swept by app/files/jobs.py's cleanup job, not a bare Mongo TTL index
# (which can expire the Mongo doc but can never delete the corresponding
# R2 object). 24h comfortably exceeds any real parsing latency.
ABANDONED_TTL_HOURS = 24


class UnsupportedFileTypeError(ValidationAppError):
    message = "Unsupported file type. Upload a JPEG, PNG, or WEBP image."


class FileTooLargeError(ValidationAppError):
    message = "File is too large."


def _parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise NotFoundError() from exc


def _reencode_image(raw: bytes) -> tuple[bytes, str, str]:
    """Decodes `raw`, validates it's actually one of the allowed image
    formats (checked against real content, never the client-supplied
    Content-Type header — docs/SECURITY.md's file-upload threat row), and
    re-encodes it to fresh bytes. Re-encoding (rather than passing the
    original bytes through) is what strips embedded scripts/metadata/EXIF
    and defeats disguised-file-type tricks — a polyglot or fake-extension
    file that isn't actually a valid image fails to decode here.

    Returns (encoded_bytes, content_type, file_extension).
    Raises UnsupportedFileTypeError for anything that doesn't decode as an
    allowed format, or whose dimensions exceed the decompression-bomb
    guard.
    """
    try:
        with Image.open(BytesIO(raw)) as img:
            fmt = img.format
            if fmt not in _ALLOWED_FORMATS:
                raise UnsupportedFileTypeError()

            width, height = img.size
            if (
                width > _MAX_PIXEL_DIMENSION
                or height > _MAX_PIXEL_DIMENSION
                or width * height > _MAX_TOTAL_PIXELS
            ):
                raise UnsupportedFileTypeError("Image dimensions are too large.")

            # Re-encoding via a freshly-loaded RGB frame (not `img` as-is)
            # drops any embedded EXIF/ICC/XMP metadata and any trailing
            # non-image bytes appended after the image data (a common
            # polyglot trick) — only the decoded pixel data survives.
            clean = img.convert("RGB") if fmt != "PNG" else img.convert("RGBA")
            buffer = BytesIO()
            save_kwargs: dict[str, Any] = {}
            if fmt == "JPEG":
                save_kwargs["quality"] = 90
            clean.save(buffer, format=fmt, **save_kwargs)
    except UnsupportedFileTypeError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedFileTypeError() from exc

    content_type = _ALLOWED_FORMATS[fmt]
    extension = _EXTENSION_BY_FORMAT[fmt]
    return buffer.getvalue(), content_type, extension


class FileService:
    def __init__(self, db: AsyncIOMotorDatabase, storage: StorageClient | None = None) -> None:
        self._files = FileUploadRepository(db)
        self._storage = storage or get_storage_client()

    async def upload_timetable_import(
        self, *, user_id: str, raw_bytes: bytes
    ) -> FileUploadPublic:
        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            raise FileTooLargeError()
        if not raw_bytes:
            raise UnsupportedFileTypeError()

        user_oid = _parse_object_id(user_id)
        encoded, content_type, extension = _reencode_image(raw_bytes)

        r2_key = f"timetable-imports/{user_id}/{uuid4().hex}.{extension}"
        self._storage.put(key=r2_key, data=encoded, content_type=content_type)

        doc = await self._files.create(
            user_id=user_oid,
            r2_key=r2_key,
            content_type=content_type,
            size_bytes=len(encoded),
            created_at=datetime.now(UTC),
        )
        return _to_public(doc)

    async def get_download_url(self, *, user_id: str, file_id: str) -> FileDownloadUrl:
        doc = await self._get_owned(user_id=user_id, file_id=file_id)
        url = self._storage.presign_get(
            key=doc["r2_key"], expires_in_seconds=PRESIGN_EXPIRY_SECONDS
        )
        return FileDownloadUrl(
            file_id=str(doc["_id"]), url=url, expires_in_seconds=PRESIGN_EXPIRY_SECONDS
        )

    async def delete(self, *, user_id: str, file_id: str) -> None:
        user_oid = _parse_object_id(user_id)
        file_oid = _parse_object_id(file_id)
        doc = await self._files.delete_owned(file_id=file_oid, user_id=user_oid)
        if doc is None:
            raise NotFoundError()
        try:
            self._storage.delete(key=doc["r2_key"])
        except ObjectNotFoundError:
            # Already gone from storage (e.g. a previous cleanup pass
            # raced this call) — the Mongo doc is what mattered to the
            # caller, and it's already deleted. Not an error per
            # RULES.md #10-12 (idempotent at-least-once handling).
            pass

    async def _get_owned(self, *, user_id: str, file_id: str) -> dict[str, Any]:
        user_oid = _parse_object_id(user_id)
        file_oid = _parse_object_id(file_id)
        # Ownership re-verified server-side on every retrieval, per
        # RULES.md #4 — an existing file_id is never sufficient on its own.
        doc = await self._files.find_owned(file_id=file_oid, user_id=user_oid)
        if doc is None:
            raise NotFoundError()
        return doc


def _to_public(doc: dict[str, Any]) -> FileUploadPublic:
    return FileUploadPublic(
        id=str(doc["_id"]),
        content_type=doc["content_type"],
        size_bytes=doc["size_bytes"],
        status=doc["status"],
        created_at=doc["created_at"],
    )
