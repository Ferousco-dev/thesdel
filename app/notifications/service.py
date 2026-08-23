"""Notification module service. Owns device-token registration and the
push-enqueue entry points other feature modules call — per
docs/ARCHITECTURE.md §11, `announcements` and `litheral/life` import this
module's service (never the reverse, and never this module's repository
from theirs — RULES.md #19).

Scope note: study-block reminders (Premium/Pro) are explicitly NOT built
here — they're time-based/scheduled rather than event-triggered, which
needs a scheduling mechanism (periodic ARQ cron scan or per-block
scheduled jobs) beyond simple enqueue-on-event. See docs/DECISIONS.md
ADR-013.
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.notifications.repository import DeviceTokenRepository
from app.notifications.schemas import DeviceTokenPublic
from app.shared.errors import NotFoundError
from app.shared.jobs import enqueue_push_to_user
from app.shared.logging import get_logger

logger = get_logger("notifications.service")

# Dedup TTL for the enqueue-time guard — see _dedup_or_skip below and
# docs/DECISIONS.md ADR-013's dedup-mechanism note. 5 minutes is generous
# enough to collapse a retried request/duplicate trigger call, short
# enough that a genuinely new event for the same source shortly after
# still gets its own push.
_DEDUP_TTL_SECONDS = 300


class NotificationService:
    def __init__(self, db: AsyncIOMotorDatabase, redis: Redis) -> None:
        self._repo = DeviceTokenRepository(db)
        self._redis = redis

    # -- device token management ------------------------------------

    async def register_device(
        self, *, user_id: str, token: str, platform: str
    ) -> DeviceTokenPublic:
        doc = await self._repo.upsert(user_id=ObjectId(user_id), token=token, platform=platform)
        return _to_public(doc)

    async def unregister_device(self, *, user_id: str, token: str) -> None:
        deleted = await self._repo.delete(user_id=ObjectId(user_id), token=token)
        if not deleted:
            # Either the token never existed, or it belongs to someone
            # else — same response either way so this never confirms/denies
            # another user's token (RULES.md #2/#4, mirrors the
            # class-membership 404-not-403 convention in shared/deps.py).
            raise NotFoundError()

    # -- trigger entry points -----------------------------------------

    async def notify_announcement_posted(
        self,
        *,
        class_id: str,
        announcement_id: str,
        posted_by: str,
        member_user_ids: list[str],
        pinned: bool,
    ) -> None:
        """Fans a push out to every class member except the poster. Callers
        (app/announcements/service.py) resolve `member_user_ids` via
        `ClassService.list_member_user_ids` — notifications never reaches
        into `classes`' repository itself.
        """
        if not await self._dedup_or_skip("announcement_new", announcement_id):
            return

        if pinned:
            title = "📌 New pinned announcement"
            body = "Your class rep pinned a new announcement."
        else:
            title = "New class announcement"
            body = "Your class rep posted a new announcement."
        data = {
            "type": "announcement_new",
            "class_id": class_id,
            "announcement_id": announcement_id,
            "pinned": str(pinned).lower(),
        }

        for member_id in member_user_ids:
            if member_id == posted_by:
                continue
            await enqueue_push_to_user(user_id=member_id, title=title, body=body, data=data)

    async def notify_life_schedule_conflict(self, *, user_id: str) -> None:
        """Exactly one push per regenerate/adjust run that produced at
        least one conflicting block — never one push per conflicting
        block. Caller (app/litheral/life/service.py) passes a single call
        regardless of how many blocks conflicted."""
        # Dedup key includes user_id since this is a per-user trigger (no
        # shared source document id to key off, unlike the announcement
        # case) — see docs/DECISIONS.md ADR-013.
        if not await self._dedup_or_skip("life_conflict", user_id):
            return

        await enqueue_push_to_user(
            user_id=user_id,
            title="Schedule conflict detected",
            body="Your Pro life schedule has a conflict — review it in Litheral.",
            data={"type": "life_conflict"},
        )

    # -- internal --------------------------------------------------------

    async def _dedup_or_skip(self, notification_type: str, source_id: str) -> bool:
        """Returns True if this is the first call for this
        {notification_type, source_id} within the dedup window (caller
        should proceed), False if a duplicate (caller should skip).

        Per docs/ARCHITECTURE.md §7/§8: notification jobs are naturally
        safe to over-send, but are still deduplicated to avoid spamming
        users — this is that dedup, implemented as a Redis SETNX-with-TTL
        guard at enqueue time rather than a generic notification-log
        collection (RULES.md #23 — no speculative abstraction).
        """
        key = f"notif:dedup:{notification_type}:{source_id}"
        try:
            acquired = await self._redis.set(key, "1", nx=True, ex=_DEDUP_TTL_SECONDS)
        except Exception:
            # Redis hiccup: fail open (send) rather than silently dropping
            # a real notification — over-sending is the documented-safe
            # direction per ARCHITECTURE.md §7/§8, unlike rate-limiting or
            # AI-cap enforcement which fail closed.
            logger.error(
                "notifications_service.dedup_check_failed", notification_type=notification_type
            )
            return True
        return bool(acquired)


def _to_public(doc: dict) -> DeviceTokenPublic:
    return DeviceTokenPublic(
        id=str(doc["_id"]),
        platform=doc["platform"],
        created_at=doc["created_at"],
        last_seen_at=doc["last_seen_at"],
    )
