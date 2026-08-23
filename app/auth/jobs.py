"""ARQ job implementations for auth's transactional email — email
verification and password reset. Registered into the worker process by
`app/shared/jobs.py`'s `WorkerSettings` (the module that owns `arq`
wiring); this module owns the actual sending logic and stays inside
`app/auth/`'s boundary, per AGENTS.md module ownership.

See docs/ARCHITECTURE.md §8 for the retry/idempotency policy implemented
here: exponential backoff, max 5 attempts, then dead-letter (structured
log, no new alerting infra); email jobs check a `sent_at` marker before
sending so an at-least-once-delivered retry doesn't double-send.
"""

from typing import Any

from arq import Retry

from app.auth.repository import AuthTokenRepository
from app.shared.db import get_db
from app.shared.email import send_email
from app.shared.logging import get_logger
from app.shared.security import hash_opaque_token

logger = get_logger("auth.jobs")

MAX_TRIES = 5


async def send_verification_email(
    ctx: dict[str, Any], *, user_id: str, email: str, token: str
) -> None:
    await _send_token_email(
        ctx,
        user_id=user_id,
        email=email,
        token=token,
        subject="Verify your Thesdel email",
        link_path="verify-email",
    )


async def send_password_reset_email(
    ctx: dict[str, Any], *, user_id: str, email: str, token: str
) -> None:
    await _send_token_email(
        ctx,
        user_id=user_id,
        email=email,
        token=token,
        subject="Reset your Thesdel password",
        link_path="reset-password",
    )


async def _send_token_email(
    ctx: dict[str, Any], *, user_id: str, email: str, token: str, subject: str, link_path: str
) -> None:
    tokens = AuthTokenRepository(get_db())
    token_hash = hash_opaque_token(token)
    record = await tokens.find_by_hash(token_hash)
    if record is None:
        # The token was invalidated/rotated away (e.g. superseded by a
        # newer request) before this job ran — nothing to send. IDs only,
        # no PII, per RULES.md #14.
        logger.info("auth_jobs.token_gone", user_id=user_id)
        return
    if record.get("sent_at") is not None:
        # Idempotency marker — an at-least-once-delivered retry of this
        # exact job is a no-op if a previous attempt already sent it.
        logger.info("auth_jobs.already_sent", user_id=user_id)
        return

    link = f"https://app.thesdel.com/{link_path}?token={token}"
    try:
        await send_email(
            to=email,
            subject=subject,
            html=f'<p>{subject}:</p><p><a href="{link}">{link}</a></p>',
        )
    except Exception as exc:
        job_try = ctx.get("job_try", 1)
        if job_try >= MAX_TRIES:
            # Dead-letter: logged, not silently dropped. No new alerting
            # infra per task scope — this is the structured-log dead-letter
            # docs/ARCHITECTURE.md §8 calls for.
            logger.error("auth_jobs.dead_letter", user_id=user_id, job_try=job_try)
            return
        # Exponential backoff: 2s, 4s, 8s, 16s, ...
        raise Retry(defer=2**job_try) from exc

    await tokens.mark_sent(record["_id"])
