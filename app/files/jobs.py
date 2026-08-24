"""Cleanup for abandoned timetable-import uploads.

docs/PRIVACY.md §3: uploaded timetable-import images are "deleted after
successful parsing, or after a bounded TTL if parsing fails/is
abandoned (not indefinitely retained)". A bare Mongo TTL index on
`file_uploads.created_at` cannot satisfy this alone — it would delete the
Mongo *document* but leave the corresponding R2 *object* orphaned
forever, since TTL expiry never touches other systems. This periodic ARQ
job (registered as a cron job in app/worker.py, per docs/ARCHITECTURE.md
§8) sweeps stale `pending_parse` records and deletes both the Mongo doc
and the R2 object together — see docs/DECISIONS.md ADR-014.

Idempotent per RULES.md #10-12: re-running against a record already
cleaned up (or never existed) is a no-op, not an error — both storage
delete and the Mongo delete are safe to repeat.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.files.repository import FileUploadRepository
from app.files.service import ABANDONED_TTL_HOURS
from app.shared.db import get_db
from app.shared.logging import get_logger
from app.shared.storage import ObjectNotFoundError, get_storage_client

logger = get_logger("files.jobs")


async def cleanup_abandoned_file_uploads(ctx: dict[str, Any]) -> int:
    """Deletes `pending_parse` file_uploads (and their R2 objects) older
    than `ABANDONED_TTL_HOURS`. Returns the count cleaned up (useful in
    tests and worker logs)."""
    repo = FileUploadRepository(get_db())
    storage = get_storage_client()
    cutoff = datetime.now(UTC) - timedelta(hours=ABANDONED_TTL_HOURS)

    stale = await repo.find_stale_pending(older_than=cutoff)
    cleaned = 0
    for doc in stale:
        try:
            storage.delete(key=doc["r2_key"])
        except ObjectNotFoundError:
            pass
        await repo.delete_by_id(doc["_id"])
        cleaned += 1

    if cleaned:
        # IDs/counts only, no PII, per RULES.md #14.
        logger.info("files_jobs.cleanup_abandoned", cleaned_count=cleaned)
    return cleaned
