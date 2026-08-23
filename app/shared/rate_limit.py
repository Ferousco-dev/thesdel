"""Redis-backed sliding-window-ish rate limiter (fixed-window counter, atomic
INCR+EXPIRE — see docs/DECISIONS.md ADR-004 for why this primitive was chosen).

Failure behavior on Redis being down differs by criticality, per
docs/ARCHITECTURE.md §7:
  - fail_closed=True  (default): reject the request if Redis is unreachable.
    Used for auth endpoints and AI usage caps — security/cost-critical.
  - fail_closed=False: allow the request if Redis is unreachable. Used for
    general read-endpoint limiting so a Redis outage doesn't take down basic
    read access.
"""

from redis.asyncio import Redis

from app.shared.errors import RateLimitedError, ServiceUnavailableError


async def check_rate_limit(
    redis: Redis,
    *,
    key: str,
    max_requests: int,
    window_seconds: int,
    fail_closed: bool = True,
) -> None:
    try:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window_seconds)
    except Exception as exc:
        if fail_closed:
            raise ServiceUnavailableError("Rate limiting is temporarily unavailable.") from exc
        return

    if current > max_requests:
        ttl = await redis.ttl(key)
        raise RateLimitedError(details={"retry_after_seconds": max(ttl, 1)})
