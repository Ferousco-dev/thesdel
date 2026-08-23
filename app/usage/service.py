"""AI usage-cap enforcement. See docs/DECISIONS.md ADR-004 and
docs/ARCHITECTURE.md §7.

Enforcement point is a Redis atomic INCR/EXPIRE, keyed to the current
calendar-month billing period (V1 simplification — `users.tier_renewed_at`-
based periods are a documented future refinement, not yet wired up).
`ai_usage_log` in Mongo is the durable audit trail, written on every
attempt regardless of outcome, but is never the thing a concurrent request
races against — that would reopen the exact TOCTOU race ADR-004 exists to
close.
"""

from datetime import UTC, datetime
from typing import NamedTuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.shared.errors import CapReachedError, ServiceUnavailableError
from app.usage.repository import AiUsageRepository

UNLIMITED = -1  # sentinel: attempt is always logged, but never rejected


class CapStatus(NamedTuple):
    used: int
    limit: int
    resets_at: datetime


def _current_period_key() -> str:
    now = datetime.now(UTC)
    return f"{now.year:04d}-{now.month:02d}"


def _period_start() -> datetime:
    now = datetime.now(UTC)
    return datetime(now.year, now.month, 1, tzinfo=UTC)


def _period_reset_at() -> datetime:
    now = datetime.now(UTC)
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=UTC)
    return datetime(now.year, now.month + 1, 1, tzinfo=UTC)


def _seconds_until_reset() -> int:
    return max(1, int((_period_reset_at() - datetime.now(UTC)).total_seconds()))


class AiUsageService:
    def __init__(self, db: AsyncIOMotorDatabase, redis: Redis) -> None:
        self._db = db
        self._redis = redis
        self._repo = AiUsageRepository(db)

    async def check_and_reserve(self, *, user_id: str, feature: str, limit: int) -> ObjectId:
        """Atomically checks the cap and reserves one unit of it, then logs
        the attempt. Raises CapReachedError before any AI cost is incurred
        if the cap is already used up. Returns the ai_usage_log id so the
        caller can mark the outcome after the generation attempt finishes.
        """
        key = f"aicap:{user_id}:{feature}:{_current_period_key()}"

        if limit != UNLIMITED:
            try:
                current = await self._redis.incr(key)
                if current == 1:
                    await self._redis.expire(key, _seconds_until_reset())
            except CapReachedError:
                raise
            except Exception as exc:
                # AI cap enforcement fails closed — this is the product's
                # primary cost-control mechanism, per docs/ARCHITECTURE.md
                # §7 and the Backend Spec's own priority ordering. A Redis
                # outage must not silently remove it.
                raise ServiceUnavailableError(
                    "AI generation is temporarily unavailable."
                ) from exc
            if current > limit:
                raise CapReachedError(
                    details={
                        "resets_at": _period_reset_at().isoformat(),
                        "limit": limit,
                    }
                )

        return await self._repo.log_attempt(user_id=user_id, feature=feature)

    async def mark_succeeded(self, log_id: ObjectId, *, tokens_used: int | None = None) -> None:
        await self._repo.mark_outcome(log_id, status="succeeded", tokens_used=tokens_used)

    async def mark_failed(self, log_id: ObjectId) -> None:
        # Attempt already consumed a cap unit and is already logged — a
        # failed attempt is NOT refunded, which prevents a cap-bypass-via-
        # induced-failure abuse vector. See docs/ARCHITECTURE.md §13.
        await self._repo.mark_outcome(log_id, status="failed")

    async def get_status(self, *, user_id: str, feature: str, limit: int) -> CapStatus:
        used = await self._repo.count_for_period(
            user_id=user_id, feature=feature, period_start=_period_start()
        )
        return CapStatus(used=used, limit=limit, resets_at=_period_reset_at())
