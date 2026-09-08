"""ARQ cron jobs for study-block reminders (Premium/Pro feature).

Two jobs run on a schedule:
1. check_study_blocks_1day_before — daily job scanning for blocks starting in 24±1h
2. check_study_blocks_1hour_before — hourly job scanning for blocks starting in 60±5min

Both use Redis dedup (SETNX with TTL) to avoid spamming users with duplicate
notifications. See docs/ARCHITECTURE.md §8 and docs/DECISIONS.md ADR-013 for
why dedup is at enqueue time rather than a notification-log collection.

Idempotency: jobs are idempotent and safe to retry — re-running them just
re-checks and skips users who already got a notification (Redis dedup TTL).
"""

from datetime import UTC, datetime, timedelta, time
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.shared.db import get_db
from app.shared.logging import get_logger
from app.shared.redis_client import get_redis
from app.shared.jobs import enqueue_push_to_user

logger = get_logger("study.jobs")

# Dedup window: 24 hours for the 1-day reminder so a re-run doesn't spam
_DEDUP_TTL_1DAY = 24 * 60 * 60
# Dedup window: 1 hour for the 1-hour reminder so a re-run doesn't spam
_DEDUP_TTL_1HOUR = 60 * 60


async def check_study_blocks_1day_before(ctx: dict[str, Any]) -> None:
    """Daily cron job: scan for study blocks starting in ~24 hours (24±1h window)
    and enqueue a reminder push for each user. Idempotent via Redis dedup.
    """
    db = get_db()
    redis = get_redis()
    now = datetime.now(UTC)

    # Calculate the time window: now + 24h ±1h (23h to 25h from now)
    target_start = now + timedelta(hours=23)
    target_end = now + timedelta(hours=25)

    # Query for Premium/Pro users only (tier is premium or pro)
    users = await db.users.find({"tier": {"$in": ["premium", "pro"]}}).to_list(None)
    if not users:
        logger.info("study_jobs.1day_no_users")
        return

    for user in users:
        user_id = str(user["_id"])
        await _check_and_notify_for_user(
            db=db,
            redis=redis,
            user_id=user_id,
            target_start=target_start,
            target_end=target_end,
            window_name="1day",
            dedup_ttl=_DEDUP_TTL_1DAY,
            message_suffix="in 1 day",
        )


async def check_study_blocks_1hour_before(ctx: dict[str, Any]) -> None:
    """Hourly cron job: scan for study blocks starting in ~1 hour (60±5min window)
    and enqueue a reminder push for each user. Idempotent via Redis dedup.
    """
    db = get_db()
    redis = get_redis()
    now = datetime.now(UTC)

    # Calculate the time window: now + 1h ±5min (55min to 65min from now)
    target_start = now + timedelta(minutes=55)
    target_end = now + timedelta(minutes=65)

    # Query for Premium/Pro users only
    users = await db.users.find({"tier": {"$in": ["premium", "pro"]}}).to_list(None)
    if not users:
        logger.info("study_jobs.1hour_no_users")
        return

    for user in users:
        user_id = str(user["_id"])
        await _check_and_notify_for_user(
            db=db,
            redis=redis,
            user_id=user_id,
            target_start=target_start,
            target_end=target_end,
            window_name="1hour",
            dedup_ttl=_DEDUP_TTL_1HOUR,
            message_suffix="in 1 hour",
        )


async def _check_and_notify_for_user(
    *,
    db: AsyncIOMotorDatabase,
    redis: Redis,
    user_id: str,
    target_start: datetime,
    target_end: datetime,
    window_name: str,
    dedup_ttl: int,
    message_suffix: str,
) -> None:
    """Helper: for a single user, find study blocks in the target time window
    and enqueue a push for each (deduplicated). No PII in logs per RULES.md #14.
    """
    study_plans = await db.study_plans.find({"user_id": ObjectId(user_id)}).to_list(None)
    if not study_plans:
        return

    for block in study_plans:
        # Calculate the next occurrence of this recurring weekly block
        next_occurrence = _next_occurrence_of_weekly_block(block, target_start)

        # Check if it falls within the target window
        if target_start <= next_occurrence <= target_end:
            subject = block.get("subject", "Study")
            dedup_key = f"reminder:{window_name}:{user_id}:{str(block['_id'])}"

            # Dedup: only send if we haven't sent one for this {user, block, window} recently
            if not await _dedup_or_skip(redis, dedup_key, dedup_ttl):
                logger.info("study_jobs.dedup_skipped", user_id=user_id, window=window_name)
                continue

            # Enqueue the push
            await enqueue_push_to_user(
                user_id=user_id,
                title=f"Study session: {subject} {message_suffix}",
                body=f"Your {subject} study block is {message_suffix}.",
                data={
                    "type": "study_reminder",
                    "window": window_name,
                    "block_id": str(block["_id"]),
                    "subject": subject,
                },
            )
            logger.info("study_jobs.push_enqueued", user_id=user_id, window=window_name)


def _next_occurrence_of_weekly_block(
    block: dict[str, Any], reference_time: datetime
) -> datetime:
    """Calculate when a weekly recurring block (defined by day_of_week + start_time)
    next occurs relative to a reference time.

    The study_plans collection stores:
    - day_of_week: 0-6 (Monday=0, Sunday=6)
    - start_time: "HH:MM" string

    This function finds the next datetime when the block starts, given a reference
    point in time (typically "now" or a target window start).
    """
    day_of_week = block["day_of_week"]
    start_time_str = block["start_time"]

    # Parse start_time (HH:MM format)
    hours, minutes = start_time_str.split(":")
    start_hour = int(hours)
    start_minute = int(minutes)

    # reference_time is a datetime in UTC; we work in the local timezone's day
    # structure (day_of_week). Since study_plans are created in the user's local
    # timezone but stored as day_of_week (0-6) + time_string, we assume the
    # reference_time is already in the user's "day space" — this job runs at
    # server time, not user-local time, so in production this would need
    # timezone awareness from the user's profile. For MVP, assume UTC alignment.
    ref_day_of_week = reference_time.weekday()

    # Calculate the target time on the target day
    if day_of_week > ref_day_of_week:
        # Target day is later this week
        days_ahead = day_of_week - ref_day_of_week
    elif day_of_week < ref_day_of_week:
        # Target day is next week
        days_ahead = 7 - (ref_day_of_week - day_of_week)
    else:
        # Same day of week — check if the time has passed today
        if (start_hour, start_minute) > (reference_time.hour, reference_time.minute):
            # Time hasn't passed today, so it's today
            days_ahead = 0
        else:
            # Time has passed, so it's next week
            days_ahead = 7

    target_date = reference_time.date() + timedelta(days=days_ahead)
    target_time = time(hour=start_hour, minute=start_minute)
    return datetime.combine(target_date, target_time, tzinfo=UTC)


async def _dedup_or_skip(redis: Redis, key: str, ttl: int) -> bool:
    """Returns True if this is the first call for `key` within the TTL window
    (caller should proceed), False if a duplicate (caller should skip).

    Uses Redis SETNX-with-TTL, same pattern as NotificationService._dedup_or_skip
    in app/notifications/service.py. Per docs/DECISIONS.md ADR-013, this dedup
    guards against re-sending to the same user on a job retry or scheduled re-run.
    """
    try:
        acquired = await redis.set(key, "1", nx=True, ex=ttl)
        return bool(acquired)
    except Exception:
        # Redis hiccup: fail open (send) rather than silently dropping — per
        # docs/ARCHITECTURE.md §7, this is the safe direction (over-sending
        # a notification is documented-acceptable, whereas silently dropping
        # one is not).
        logger.error("study_jobs.dedup_check_failed", key=key)
        return True
