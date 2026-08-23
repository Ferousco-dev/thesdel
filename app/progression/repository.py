"""Raw Mongo access for progression (badges, thesdel_score, seasons, rank).

Per docs/DATABASE.md §1 and ADR-006: `users._id` is never hard-deleted, so
records here (`user_badges`, `users.thesdel_score`) never go orphaned and
need no soft-delete/orphan handling.
"""

from datetime import UTC, date, datetime, time
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

# Badge catalog is small by design (~225 docs across ~17 families per the
# Backend Spec) — bounded read, no pagination needed, but capped defensively
# per RULES.md #6 (never an unbounded query).
_BADGE_CATALOG_HARD_CAP = 500


class BadgeRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find_by_id(self, badge_id: ObjectId) -> dict[str, Any] | None:
        return await self._db.badges.find_one({"_id": badge_id})

    async def list_all(self, *, limit: int = _BADGE_CATALOG_HARD_CAP) -> list[dict[str, Any]]:
        cursor = self._db.badges.find().limit(min(limit, _BADGE_CATALOG_HARD_CAP))
        return [doc async for doc in cursor]

    async def list_by_criteria_type(self, criteria_type: str) -> list[dict[str, Any]]:
        """Serves badge-award evaluation: given an event's criteria_type
        (e.g. "study_sessions_completed"), find all badges of that type so
        the caller can compare each one's criteria_value against the
        user's current progress. See docs/DATABASE.md query-pattern table.
        """
        cursor = self._db.badges.find({"criteria_type": criteria_type}).limit(
            _BADGE_CATALOG_HARD_CAP
        )
        return [doc async for doc in cursor]

    async def create(
        self, *, family: str, name: str, criteria_type: str, criteria_value: Any
    ) -> dict[str, Any]:
        doc = {
            "family": family,
            "name": name,
            "criteria_type": criteria_type,
            "criteria_value": criteria_value,
        }
        result = await self._db.badges.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc


class UserBadgeRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def award(self, *, user_id: ObjectId, badge_id: ObjectId) -> bool:
        """Idempotent award. Returns True if this call newly awarded the
        badge, False if the user already had it. A duplicate-key hit on the
        unique compound index `{user_id, badge_id}` (docs/DATABASE.md §1) is
        treated as success, not an error — at-least-once triggering is
        assumed per RULES.md #10-12.
        """
        doc = {
            "user_id": user_id,
            "badge_id": badge_id,
            "earned_at": datetime.now(UTC),
        }
        try:
            await self._db.user_badges.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def has_badge(self, *, user_id: ObjectId, badge_id: ObjectId) -> bool:
        existing = await self._db.user_badges.find_one(
            {"user_id": user_id, "badge_id": badge_id}, {"_id": 1}
        )
        return existing is not None

    async def list_for_user(self, user_id: ObjectId) -> list[dict[str, Any]]:
        # Bounded by the badge catalog size (~225 max) — a user can never
        # earn more badges than exist, so no separate limit is needed.
        cursor = self._db.user_badges.find({"user_id": user_id})
        return [doc async for doc in cursor]


class ProgressionUserRepository:
    """Progression's own narrow view of `users` — only the two fields this
    module owns mutation of (`thesdel_score`, `rank`). Never reads/writes
    `tier` — that stays billing-only per RULES.md forbidden patterns.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find_by_id(self, user_id: ObjectId) -> dict[str, Any] | None:
        return await self._db.users.find_one({"_id": user_id}, {"thesdel_score": 1, "rank": 1})

    async def increment_score(self, user_id: ObjectId, amount: int) -> int | None:
        """Atomic, monotonically-increasing $inc. Caller (service layer)
        enforces amount > 0 — this repository method never accepts a
        negative delta, matching "thesdel_score never decreases via
        progression endpoints"."""
        result = await self._db.users.find_one_and_update(
            {"_id": user_id},
            {"$inc": {"thesdel_score": amount}},
            return_document=True,
            projection={"thesdel_score": 1},
        )
        return result["thesdel_score"] if result else None

    async def set_rank(self, user_id: ObjectId, rank: str) -> None:
        await self._db.users.update_one({"_id": user_id}, {"$set": {"rank": rank}})


def _as_datetime(value: date) -> datetime:
    # BSON has no native "date" (only UTC datetime) — `seasons.start_date` /
    # `end_date` are conceptually calendar dates but stored as UTC midnight
    # datetimes, matching how MongoDB actually represents this everywhere
    # else in this codebase (e.g. ai_usage_log.created_at).
    return datetime.combine(value, time.min, tzinfo=UTC)


class SeasonRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def find_current(self, *, on: date) -> dict[str, Any] | None:
        """Serves "what season is it right now" — see docs/DATABASE.md
        query-pattern table."""
        on_dt = _as_datetime(on)
        return await self._db.seasons.find_one(
            {"start_date": {"$lte": on_dt}, "end_date": {"$gte": on_dt}}
        )

    async def create(self, *, start_date: date, end_date: date) -> dict[str, Any]:
        doc = {"start_date": _as_datetime(start_date), "end_date": _as_datetime(end_date)}
        result = await self._db.seasons.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc
