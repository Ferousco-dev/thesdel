"""ARQ worker entrypoint. Run with:

    arq app.worker.WorkerSettings

Wires each module's job *implementations* (currently just
`app/auth/jobs.py`) into the worker process. `app/shared/jobs.py` is the
registry other modules enqueue jobs through by name — it does not import
job implementations itself, to avoid a shared-module -> feature-module
import cycle; this file is the one place that imports both and connects
them. See docs/ARCHITECTURE.md §8 and docs/DECISIONS.md ADR-010.
"""

from typing import Any

from arq.connections import RedisSettings

from app.auth.jobs import send_password_reset_email, send_verification_email
from app.notifications.jobs import send_push_to_user
from app.shared.config import get_settings
from app.shared.db import close_client
from app.shared.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("worker")


async def _on_startup(ctx: dict[str, Any]) -> None:
    logger.info("worker.startup")


async def _on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker.shutdown")
    await close_client()


class WorkerSettings:
    functions = [send_verification_email, send_password_reset_email, send_push_to_user]
    # Same Redis connection config as the rest of the app
    # (app/shared/config.py) — no second, hardcoded Redis URL.
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    on_startup = _on_startup
    on_shutdown = _on_shutdown
    # arq's own attempt counter; app/auth/jobs.py makes the dead-letter
    # decision itself at MAX_TRIES=5, so this is one higher purely so arq
    # never gives up before that dead-letter log line has a chance to fire.
    max_tries = 6
