"""Thin Resend REST API wrapper — plain-text/simple-HTML message sending
only, no templating system (per task scope). Calls Resend's HTTP API
directly via `httpx` rather than adding the `resend` SDK as a dependency:
`httpx` is already installed (used by the test suite, and retained in the
production image — see `Dockerfile`), and sending one email is a single
POST, not worth a new dependency for.

If `resend_api_key` is unset (the local/test default), sending is a
no-op — dev/test environments never hard-fail on a missing API key, per
the task's explicit requirement.
"""

import httpx

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger("email")

_RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str) -> None:
    """Sends one transactional email. Raises on a real send failure (the
    caller — an ARQ job — is expected to retry); no-ops quietly when no API
    key is configured.

    Never logs the recipient address or message content (PII) — see
    RULES.md #14.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.info("email.noop_missing_api_key")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        response.raise_for_status()
    logger.info("email.sent")
