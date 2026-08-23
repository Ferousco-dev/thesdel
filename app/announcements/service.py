import base64
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.announcements.repository import AnnouncementRepository
from app.announcements.schemas import AnnouncementCreate, AnnouncementPage, AnnouncementPublic
from app.shared.errors import NotFoundError

_DEFAULT_PAGE_SIZE = 20


class AnnouncementService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = AnnouncementRepository(db)

    async def post(self, *, class_id: str, posted_by: str, body: AnnouncementCreate) -> AnnouncementPublic:
        doc = await self._repo.create(
            class_id=ObjectId(class_id), posted_by=ObjectId(posted_by), content=body.content
        )
        return _to_public(doc)

    async def list_feed(
        self, *, class_id: str, cursor: str | None, limit: int = _DEFAULT_PAGE_SIZE
    ) -> AnnouncementPage:
        class_oid = ObjectId(class_id)

        pinned: list[dict] = []
        if cursor is None:
            # Pinned items only appear on the first page — subsequent pages
            # continue through the unpinned feed only, per
            # docs/Frontend Spec §4.5 ("pinned appear at top").
            pinned = await self._repo.list_pinned(class_oid)

        before = _decode_cursor(cursor) if cursor else None
        unpinned = await self._repo.list_unpinned_page(class_oid, before=before, limit=limit)

        next_cursor = None
        if len(unpinned) == limit:
            last = unpinned[-1]
            next_cursor = _encode_cursor(last["created_at"], last["_id"])

        items = [_to_public(doc) for doc in [*pinned, *unpinned]]
        return AnnouncementPage(items=items, next_cursor=next_cursor)

    async def update(
        self, *, announcement_id: str, content: str | None, pinned: bool | None
    ) -> AnnouncementPublic:
        doc = await self._require_exists(announcement_id)
        fields = {}
        if content is not None:
            fields["content"] = content
        if pinned is not None:
            fields["pinned"] = pinned
        if not fields:
            return _to_public(doc)
        updated = await self._repo.update(doc["_id"], fields)
        return _to_public(updated)

    async def _require_exists(self, announcement_id: str) -> dict:
        doc = await self._repo.find_by_id(announcement_id)
        if doc is None:
            raise NotFoundError()
        return doc


def _encode_cursor(created_at: datetime, obj_id: ObjectId) -> str:
    raw = f"{created_at.isoformat()}|{obj_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, obj_id_raw = raw.split("|", 1)
    return datetime.fromisoformat(created_at_raw), ObjectId(obj_id_raw)


def _to_public(doc: dict) -> AnnouncementPublic:
    return AnnouncementPublic(
        id=str(doc["_id"]),
        class_id=str(doc["class_id"]),
        posted_by=str(doc["posted_by"]),
        content=doc["content"],
        pinned=doc["pinned"],
        created_at=doc["created_at"],
    )
