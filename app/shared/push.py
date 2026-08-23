"""Thin FCM push wrapper — sends a single push to a single device token, no
templating system (per task scope), mirroring `app/shared/email.py`'s
"thin wrapper, no-ops without config" shape.

Uses FCM's legacy HTTP API (`fcm.googleapis.com/fcm/send`, server-key
auth) via `httpx`, which is already a dependency — see
docs/DECISIONS.md ADR-012 for why this was picked over FCM HTTP v1
(which needs OAuth2 tokens minted from a service account, effectively
requiring the `firebase-admin` or `google-auth` dependency).

If `fcm_server_key` is unset (the local/test default), sending is a
no-op — dev/test environments never hard-fail on missing push config,
same as `send_email`.
"""

import httpx

from app.shared.config import get_settings
from app.shared.logging import get_logger

logger = get_logger("push")

_FCM_SEND_URL = "https://fcm.googleapis.com/fcm/send"

# FCM error codes that mean the token itself is dead and should be pruned
# rather than retried — see app/notifications/jobs.py.
INVALID_TOKEN_ERRORS = {"NotRegistered", "InvalidRegistration", "MismatchSenderId"}


class PushTokenInvalidError(Exception):
    """Raised when FCM reports the token is dead/invalid — the caller
    should prune it from `device_tokens` rather than retry."""


async def send_push(
    *, token: str, title: str, body: str, data: dict[str, str] | None = None
) -> None:
    """Sends one push notification to one device token.

    Raises `PushTokenInvalidError` when FCM reports the token as dead
    (caller prunes it). Raises a generic exception on any other send
    failure (the caller — an ARQ job — is expected to retry). No-ops
    quietly when no FCM server key is configured.

    Never logs the notification title/body (PII/user content) — see
    RULES.md #14.
    """
    settings = get_settings()
    if not settings.fcm_server_key:
        logger.info("push.noop_missing_server_key")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _FCM_SEND_URL,
            headers={
                "Authorization": f"key={settings.fcm_server_key}",
                "Content-Type": "application/json",
            },
            json={
                "to": token,
                "notification": {"title": title, "body": body},
                "data": data or {},
            },
        )
        response.raise_for_status()
        payload = response.json()

    if payload.get("failure", 0) >= 1:
        results = payload.get("results") or [{}]
        error = results[0].get("error")
        if error in INVALID_TOKEN_ERRORS:
            raise PushTokenInvalidError(error)
        raise RuntimeError(f"fcm_send_failed:{error}")

    logger.info("push.sent")
