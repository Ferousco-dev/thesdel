"""ARQ job registry — the one place other modules enqueue background jobs
from, instead of scattering raw ARQ pool calls through service code.

See docs/ARCHITECTURE.md §7/§8. The pool is created lazily against the same
Redis config the rest of the app uses (`app/shared/config.py`) — no second
Redis URL. Job *implementations* live in the owning module (e.g.
`app/auth/jobs.py`) and are wired into the worker process by `app/worker.py`
(the `arq` entrypoint, `arq app.worker.WorkerSettings`) — deliberately not
imported here, to avoid a shared-module -> feature-module import. This
module only knows job *names* and how to enqueue them.

Per docs/ARCHITECTURE.md §7 ("ARQ job enqueue: jobs queue in-memory
briefly and retry enqueue; if Redis stays down ... surface a clear
'processing delayed' state rather than a silent failure"), a transient
enqueue failure never fails the calling request — every `enqueue_*`
function here logs and continues instead of raising. The corresponding
user-facing action (e.g. registration) still succeeds; the email will
simply be delayed until the next request re-triggers it or an operator
notices the dead-letter log.
"""

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger("jobs")

JOB_SEND_VERIFICATION_EMAIL = "send_verification_email"
JOB_SEND_PASSWORD_RESET_EMAIL = "send_password_reset_email"
JOB_SEND_PUSH_TO_USER = "send_push_to_user"

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def _enqueue(job_name: str, /, **kwargs: Any) -> None:
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job(job_name, **kwargs)
    except Exception:
        # Never let a queue-backend hiccup fail the calling request — see
        # module docstring and docs/ARCHITECTURE.md §7. No PII in the log.
        logger.error("job.enqueue_failed", job_name=job_name)


async def enqueue_email_verification(*, user_id: str, email: str, token: str) -> None:
    await _enqueue(JOB_SEND_VERIFICATION_EMAIL, user_id=user_id, email=email, token=token)


async def enqueue_password_reset_email(*, user_id: str, email: str, token: str) -> None:
    await _enqueue(JOB_SEND_PASSWORD_RESET_EMAIL, user_id=user_id, email=email, token=token)


async def enqueue_push_to_user(
    *, user_id: str, title: str, body: str, data: dict[str, str] | None = None
) -> None:
    await _enqueue(JOB_SEND_PUSH_TO_USER, user_id=user_id, title=title, body=body, data=data or {})
