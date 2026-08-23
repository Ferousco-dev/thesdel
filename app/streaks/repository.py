"""Raw Mongo access for `partner_streaks`.

Per docs/DATABASE.md's `partner_streaks` section: a pair is always stored
normalized `user_a < user_b` (lexical string comparison of the ObjectId hex)
so the same two users can never end up with two documents representing the
same relationship in opposite field order. The unique compound index on
`{user_a, user_b}` (see `app/shared/db.py::ensure_indexes`) is the DB-level
backstop for that invariant.
"""

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError


def normalize_pair(user_id_1: ObjectId, user_id_2: ObjectId) -> tuple[ObjectId, ObjectId]:
    """Returns (user_a, user_b) with user_a < user_b, lexically, by hex
    string — matching the normalization documented in docs/DATABASE.md."""
    if str(user_id_1) < str(user_id_2):
        return user_id_1, user_id_2
    return user_id_2, user_id_1


class PartnerStreakRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find_pair(self, user_a: ObjectId, user_b: ObjectId) -> dict[str, Any] | None:
        return await self._db.partner_streaks.find_one({"user_a": user_a, "user_b": user_b})

    async def find_by_id(self, streak_id: ObjectId) -> dict[str, Any] | None:
        return await self._db.partner_streaks.find_one({"_id": streak_id})

    async def create_pending(
        self, *, user_a: ObjectId, user_b: ObjectId, invited_by: ObjectId
    ) -> dict[str, Any] | None:
        """Returns the newly created doc, or None if a doc for this
        normalized pair already exists (caller falls back to a re-fetch —
        this is the idempotent-duplicate-invite path, mirroring
        `classes.join_class`'s pre-check + DuplicateKeyError-catch pattern).
        """
        doc = {
            "user_a": user_a,
            "user_b": user_b,
            "invited_by": invited_by,
            "current_streak": 0,
            "last_interaction_at": None,
            "status": "pending",
        }
        try:
            result = await self._db.partner_streaks.insert_one(doc)
            doc["_id"] = result.inserted_id
            return doc
        except DuplicateKeyError:
            return None

    async def accept(self, *, user_a: ObjectId, user_b: ObjectId) -> dict[str, Any] | None:
        """Atomically flips a pending pair to active and stamps
        last_interaction_at. Acceptance itself counts as day 1 of the
        streak (current_streak starts at 1, not 0) — mutual opt-in is
        itself the first interaction; a same-day check-in afterwards is
        then correctly treated as an idempotent no-op by `apply_check_in`'s
        same-day dedup rather than double-counting day 1.

        Filters on status="pending" so this is a no-op (returns None) if the
        pair is already active or doesn't exist — callers distinguish those
        cases with a follow-up find_pair."""
        now = datetime.now(UTC)
        return await self._db.partner_streaks.find_one_and_update(
            {"user_a": user_a, "user_b": user_b, "status": "pending"},
            {"$set": {"status": "active", "last_interaction_at": now, "current_streak": 1}},
            return_document=True,
        )

    async def apply_check_in(
        self, *, streak_id: ObjectId, expected_last_interaction_at: datetime | None, new_streak: int
    ) -> dict[str, Any] | None:
        """Optimistic-concurrency update: only applies if
        `last_interaction_at` still matches what the caller last read.
        Returns None if it lost the race (someone else already checked in
        for today) — the service layer treats that as an idempotent no-op,
        not an error, per RULES.md #10-12."""
        now = datetime.now(UTC)
        return await self._db.partner_streaks.find_one_and_update(
            {"_id": streak_id, "last_interaction_at": expected_last_interaction_at},
            {"$set": {"current_streak": new_streak, "last_interaction_at": now}},
            return_document=True,
        )

    async def list_for_user(self, user_id: ObjectId) -> list[dict[str, Any]]:
        # Bounded: a user's partner-streak count is inherently small
        # (1:1 mutual pairs), no pagination needed, but capped defensively
        # per RULES.md #6.
        cursor = self._db.partner_streaks.find(
            {"$or": [{"user_a": user_id}, {"user_b": user_id}]}
        ).limit(500)
        return [doc async for doc in cursor]


class StreakUserLookupRepository:
    """Minimal, narrow read of `users` — only what `streaks` needs to
    validate an invite target exists, never anything from another module's
    owned fields (tier, email, etc. are not read here)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def exists(self, user_id: ObjectId) -> bool:
        doc = await self._db.users.find_one({"_id": user_id}, {"_id": 1})
        return doc is not None
