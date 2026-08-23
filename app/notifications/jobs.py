"""ARQ job implementation for push notifications. Registered into the
worker process by `app/worker.py`, following the exact pattern from
`app/auth/jobs.py`: exponential backoff, max 5 attempts, then dead-letter
(structured log, no new alerting infra) — see docs/ARCHITECTURE.md §8.

Unlike email jobs, a push job has no `sent_at` idempotency marker to
check: per docs/ARCHITECTURE.md §7/§8, notification jobs are "naturally
idempotent-safe to over-send" (a duplicate push just shows twice in a
notification tray), so this job does not need per-attempt dedup — the
dedup guard that matters lives at *enqueue* time in
`app/notifications/service.py` (a Redis SETNX per trigger), preventing
the same event from enqueueing more than once in the first place.
"""

from typing import Any

from arq import Retry
from bson import ObjectId

from app.notifications.repository import DeviceTokenRepository
from app.shared.db import get_db
from app.shared.logging import get_logger
from app.shared.push import PushTokenInvalidError, send_push

logger = get_logger("notifications.jobs")

MAX_TRIES = 5


async def send_push_to_user(
    ctx: dict[str, Any], *, user_id: str, title: str, body: str, data: dict[str, str] | None = None
) -> None:
    """Fans a single push out across every device registered to
    `user_id`. A dead/invalid token FCM reports back is pruned from
    `device_tokens` immediately rather than retried forever (RULES.md
    #10-12)."""
    repo = DeviceTokenRepository(get_db())
    tokens = await repo.list_tokens_for_user(ObjectId(user_id))
    if not tokens:
        logger.info("notifications_jobs.no_devices", user_id=user_id)
        return

    any_transient_failure = False
    for token in tokens:
        try:
            await send_push(token=token, title=title, body=body, data=data)
        except PushTokenInvalidError:
            await repo.delete_by_token(token)
            logger.info("notifications_jobs.pruned_dead_token", user_id=user_id)
        except Exception:
            any_transient_failure = True
            logger.warning("notifications_jobs.send_failed", user_id=user_id)

    if any_transient_failure:
        job_try = ctx.get("job_try", 1)
        if job_try >= MAX_TRIES:
            # Dead-letter: logged, not silently dropped — see
            # docs/ARCHITECTURE.md §8 and app/auth/jobs.py's identical
            # pattern.
            logger.error("notifications_jobs.dead_letter", user_id=user_id, job_try=job_try)
            return
        # Exponential backoff: 2s, 4s, 8s, 16s, ...
        raise Retry(defer=2**job_try)
