"""Business logic for 1:1 mutual opt-in partner streaks.

Central constraint (docs/SECURITY.md "Partner streaks" threat row): a user
must never be able to unilaterally create or activate a streak with another
user's ID. Every mutation here re-derives the normalized pair and the
caller's membership/role in it from the database — never from a
client-asserted role.

Two first-pass product decisions were not spec'd anywhere available to this
module and were made here; both are logged in docs/DECISIONS.md ADR-009:
- What counts as "interaction": an explicit daily check-in endpoint, once
  per pair per UTC calendar day.
- Stale-reset window: 48 hours since `last_interaction_at`, checked lazily
  on the next check-in rather than via a cron (RULES.md #23 — no
  speculative infra for something a lazy check handles just as well).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.progression.service import ProgressionService
from app.streaks.repository import (
    PartnerStreakRepository,
    StreakUserLookupRepository,
    normalize_pair,
)
from app.streaks.schemas import CheckInResult, StreakPublic
from app.shared.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError

STALE_WINDOW = timedelta(hours=48)

# Every Nth day of a shared streak awards a small thesdel_score bonus to
# both partners. Kept intentionally small/simple per the task's "clean,
# small addition or leave as a follow-up" guidance — no new badge family,
# no separate milestone table, just a flat award via progression's public
# service interface (never its repository, per docs/ARCHITECTURE.md §2).
_MILESTONE_INTERVAL_DAYS = 7
_MILESTONE_SCORE_AWARD = 10


def _as_aware(value: datetime) -> datetime:
    """mongomock (the in-memory Mongo used in tests) stores datetimes
    naive, dropping tzinfo on round-trip, even though everything written by
    this app is UTC. Treat a naive value as UTC rather than erroring — the
    production driver (motor, `tz_aware=True` per app/shared/db.py) never
    hits this path with a naive value in the first place."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise ValidationAppError("Invalid user id.") from exc


class StreakService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._streaks = PartnerStreakRepository(db)
        self._users = StreakUserLookupRepository(db)
        self._progression = ProgressionService(db)

    # -- invite / accept --------------------------------------------------

    async def invite(self, *, current_user_id: str, invitee_user_id: str) -> StreakPublic:
        current_oid = _parse_object_id(current_user_id)
        invitee_oid = _parse_object_id(invitee_user_id)

        if current_oid == invitee_oid:
            raise ValidationAppError("Cannot start a streak with yourself.")
        if not await self._users.exists(invitee_oid):
            raise NotFoundError("No such user.")

        user_a, user_b = normalize_pair(current_oid, invitee_oid)

        doc = await self._streaks.create_pending(
            user_a=user_a, user_b=user_b, invited_by=current_oid
        )
        if doc is None:
            # Duplicate invite attempt (or the pair already exists in some
            # state) — idempotent no-op, per RULES.md #10-12: return
            # whatever the existing state is rather than erroring.
            doc = await self._streaks.find_pair(user_a, user_b)
            if doc is None:
                raise ConflictError("Could not create the streak invite.")
        return _to_public(doc)

    async def accept(self, *, current_user_id: str, inviter_user_id: str) -> StreakPublic:
        current_oid = _parse_object_id(current_user_id)
        inviter_oid = _parse_object_id(inviter_user_id)

        user_a, user_b = normalize_pair(current_oid, inviter_oid)
        existing = await self._streaks.find_pair(user_a, user_b)
        if existing is None:
            raise NotFoundError("No such streak invite.")

        if existing["status"] == "active":
            # Duplicate accept — idempotent no-op success.
            return _to_public(existing)

        # Only the invitee (the party that did NOT send the invite) may
        # accept. The inviter re-"accepting" their own invite is rejected —
        # this is the central mutual-opt-in guarantee from
        # docs/SECURITY.md's "Partner streaks" threat row.
        if existing["invited_by"] == current_oid:
            raise ForbiddenError("Only the invited user can accept this streak.")

        updated = await self._streaks.accept(user_a=user_a, user_b=user_b)
        if updated is None:
            # Lost a race with another accept call — re-fetch current state.
            updated = await self._streaks.find_pair(user_a, user_b)
            if updated is None:
                raise ConflictError("Could not accept this streak invite.")
        return _to_public(updated)

    # -- check-in -----------------------------------------------------------

    async def check_in(self, *, current_user_id: str, partner_user_id: str) -> CheckInResult:
        current_oid = _parse_object_id(current_user_id)
        partner_oid = _parse_object_id(partner_user_id)

        user_a, user_b = normalize_pair(current_oid, partner_oid)
        doc = await self._streaks.find_pair(user_a, user_b)
        if doc is None:
            raise NotFoundError("No such streak.")

        # Authorization: the caller must actually be a member of this pair —
        # guaranteed by construction here since `current_oid` is one of the
        # two ids normalize_pair was given, but re-asserted explicitly per
        # RULES.md #4 (an ID existing/matching is never trusted implicitly
        # without this check).
        if current_oid not in (doc["user_a"], doc["user_b"]):
            raise ForbiddenError("Not a member of this streak.")

        if doc["status"] != "active":
            raise ConflictError("This streak is not active yet.")

        now = datetime.now(UTC)
        raw_last = doc["last_interaction_at"]
        last = _as_aware(raw_last) if raw_last is not None else None

        if last is not None and last.date() == now.date():
            # Already checked in today — idempotent no-op, not an error.
            return CheckInResult(streak=_to_public(doc), already_checked_in_today=True)

        stale = last is None or (now - last) > STALE_WINDOW
        new_streak = 1 if stale else doc["current_streak"] + 1

        updated = await self._streaks.apply_check_in(
            streak_id=doc["_id"], expected_last_interaction_at=raw_last, new_streak=new_streak
        )
        if updated is None:
            # Lost an optimistic-concurrency race with a concurrent check-in
            # (e.g. both partners checking in near-simultaneously) — refetch
            # and treat as already handled, per RULES.md #10-12.
            refetched = await self._streaks.find_pair(user_a, user_b)
            if refetched is None:
                raise ConflictError("Could not record this check-in.")
            return CheckInResult(streak=_to_public(refetched), already_checked_in_today=True)

        if updated["current_streak"] % _MILESTONE_INTERVAL_DAYS == 0:
            await self._progression.add_score(
                user_id=str(updated["user_a"]), amount=_MILESTONE_SCORE_AWARD
            )
            await self._progression.add_score(
                user_id=str(updated["user_b"]), amount=_MILESTONE_SCORE_AWARD
            )

        return CheckInResult(streak=_to_public(updated), already_checked_in_today=False)

    # -- reads ----------------------------------------------------------------

    async def get_with_partner(self, *, current_user_id: str, partner_user_id: str) -> StreakPublic:
        current_oid = _parse_object_id(current_user_id)
        partner_oid = _parse_object_id(partner_user_id)
        user_a, user_b = normalize_pair(current_oid, partner_oid)

        doc = await self._streaks.find_pair(user_a, user_b)
        if doc is None or current_oid not in (doc["user_a"], doc["user_b"]):
            raise NotFoundError("No such streak.")
        return _to_public(_apply_lazy_reset(doc))

    async def list_my_streaks(self, *, current_user_id: str) -> list[StreakPublic]:
        current_oid = _parse_object_id(current_user_id)
        docs = await self._streaks.list_for_user(current_oid)
        return [_to_public(_apply_lazy_reset(doc)) for doc in docs]


def _apply_lazy_reset(doc: dict[str, Any]) -> dict[str, Any]:
    """Read-time view only — does not persist. A stale streak reads as 0
    until the next check-in actually writes the reset, per the lazy-reset
    design in docs/DECISIONS.md ADR-009 (RULES.md #23: no cron needed)."""
    if doc["status"] != "active" or doc["last_interaction_at"] is None:
        return doc
    last = _as_aware(doc["last_interaction_at"])
    if (datetime.now(UTC) - last) > STALE_WINDOW and doc["current_streak"] != 0:
        doc = {**doc, "current_streak": 0}
    return doc


def _to_public(doc: dict[str, Any]) -> StreakPublic:
    return StreakPublic(
        id=str(doc["_id"]),
        user_a=str(doc["user_a"]),
        user_b=str(doc["user_b"]),
        current_streak=doc["current_streak"],
        last_interaction_at=doc["last_interaction_at"],
        status=doc["status"],
    )
