import secrets
import string

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.classes.repository import ClassMemberRepository, ClassRepository
from app.classes.schemas import ClassPreview, ClassPublic, MembershipPublic
from app.shared.db import run_in_transaction
from app.shared.errors import ConflictError, NotFoundError

_JOIN_CODE_ALPHABET = string.ascii_uppercase + string.digits
_JOIN_CODE_LENGTH = 7
_MAX_JOIN_CODE_ATTEMPTS = 5


class ClassService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._classes = ClassRepository(db)
        self._members = ClassMemberRepository(db)

    async def create_class(self, *, name: str, created_by: str) -> ClassPublic:
        join_code = await self._generate_unique_join_code()
        class_doc = await self._classes.create(name=name, created_by=created_by, join_code=join_code)
        await self._members.add(
            class_id=class_doc["_id"], user_id=ObjectId(created_by), role="rep"
        )
        return _to_public(class_doc)

    async def preview_by_join_code(self, join_code: str) -> ClassPreview:
        class_doc = await self._classes.find_by_join_code(join_code.upper())
        if class_doc is None:
            raise NotFoundError("No class found for that code.")
        return ClassPreview(
            id=str(class_doc["_id"]),
            name=class_doc["name"],
            member_count=class_doc["member_count"],
        )

    async def join_class(self, *, join_code: str, user_id: str) -> MembershipPublic:
        class_doc = await self._classes.find_by_join_code(join_code.upper())
        if class_doc is None:
            raise NotFoundError("No class found for that code.")

        class_id = class_doc["_id"]
        user_oid = ObjectId(user_id)

        existing = await self._members.find(class_id, user_oid)
        if existing is not None:
            # Idempotent: rejoining an already-joined class is a no-op
            # success, not an error — see docs/API.md §8.
            return MembershipPublic(class_id=str(class_id), role=existing["role"])

        async def _do_join(session) -> None:
            await self._members.add(
                class_id=class_id, user_id=user_oid, role="member", session=session
            )
            await self._classes.increment_member_count(class_id, session=session)

        try:
            await run_in_transaction(_do_join)
        except Exception as exc:
            # Unique compound index on {class_id, user_id} is the backstop
            # against a concurrent duplicate join racing this same check —
            # see docs/DATABASE.md §1 (class_members).
            existing = await self._members.find(class_id, user_oid)
            if existing is not None:
                return MembershipPublic(class_id=str(class_id), role=existing["role"])
            raise ConflictError("Could not join this class.") from exc

        return MembershipPublic(class_id=str(class_id), role="member")

    async def get_class(self, class_id: str) -> ClassPublic:
        class_doc = await self._classes.find_by_id(class_id)
        if class_doc is None:
            raise NotFoundError()
        return _to_public(class_doc)

    async def list_member_user_ids(self, class_id: str) -> list[str]:
        """Public read used by `app/notifications` to resolve an
        announcement-push fan-out list — per RULES.md #19/AGENTS.md module
        boundaries, other modules call this service method rather than
        reaching into `ClassMemberRepository`/`class_members` directly."""
        member_ids = await self._members.list_user_ids_for_class(ObjectId(class_id))
        return [str(uid) for uid in member_ids]

    async def _generate_unique_join_code(self) -> str:
        for _ in range(_MAX_JOIN_CODE_ATTEMPTS):
            code = "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH))
            if await self._classes.find_by_join_code(code) is None:
                return code
        raise ConflictError("Could not generate a unique join code. Please try again.")


def _to_public(class_doc: dict) -> ClassPublic:
    return ClassPublic(
        id=str(class_doc["_id"]),
        name=class_doc["name"],
        join_code=class_doc["join_code"],
        member_count=class_doc["member_count"],
        created_by=str(class_doc["created_by"]),
    )
