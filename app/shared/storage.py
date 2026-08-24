"""R2 (S3-compatible) object storage wrapper.

Only `app/files/` uses this today. Unlike email/push (which can silently
no-op and let a background job retry later, per app/shared/jobs.py's
module docstring), a file upload cannot silently no-op — the user is
waiting on it synchronously. So instead of a "log and continue" fallback,
this module picks one of two concrete backends at call time:

- `R2StorageClient` — real boto3 S3-compatible client, used whenever R2 is
  configured (`r2_account_id` and `r2_bucket_name` both set).
- `InMemoryStorageClient` — an in-process dict-backed fake, used when R2
  is not configured (local dev without R2 credentials, and every test).
  This mirrors the existing `mongomock`/`fakeredis` test-double pattern in
  `tests/conftest.py` rather than adding `moto` as a new dependency
  (RULES.md #17 — minimize dependencies; a ~40-line fake covers put/get/
  delete/presign, moto's full S3 semantics are unneeded here). See
  docs/DECISIONS.md ADR-014.

Both implement the same four operations `app/files` needs: put, get,
delete, presign. Never import `boto3` directly outside this module.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass, field
from typing import Protocol

from app.shared.config import get_settings


class ObjectNotFoundError(Exception):
    """Raised by `get`/`delete` when the key doesn't exist."""


class StorageClient(Protocol):
    def put(self, *, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, *, key: str) -> bytes: ...

    def delete(self, *, key: str) -> None: ...

    def presign_get(self, *, key: str, expires_in_seconds: int) -> str: ...


class R2StorageClient:
    """boto3 client against R2's S3-compatible endpoint
    (`https://<account_id>.r2.cloudflarestorage.com`)."""

    def __init__(self) -> None:
        settings = get_settings()
        if not (settings.r2_account_id and settings.r2_bucket_name):
            raise RuntimeError(
                "R2 is not configured (r2_account_id/r2_bucket_name missing) — "
                "set the R2_* environment variables before using R2StorageClient."
            )
        import boto3  # local import: only paid in the configured-R2 path

        self._bucket = settings.r2_bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    def put(self, *, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    def get(self, *, key: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise ObjectNotFoundError(key) from exc
        return obj["Body"].read()

    def delete(self, *, key: str) -> None:
        # S3-compatible delete_object is idempotent (no error on missing
        # key) — matches the idempotent-cleanup expectations of
        # app/files/jobs.py.
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presign_get(self, *, key: str, expires_in_seconds: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in_seconds,
        )


@dataclass
class _StoredObject:
    data: bytes
    content_type: str


@dataclass
class InMemoryStorageClient:
    """Process-local fake used for local dev without R2 credentials and
    for the test suite. Not shared across processes/workers — fine for its
    only two use cases."""

    _objects: dict[str, _StoredObject] = field(default_factory=dict)

    def put(self, *, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = _StoredObject(data=data, content_type=content_type)

    def get(self, *, key: str) -> bytes:
        obj = self._objects.get(key)
        if obj is None:
            raise ObjectNotFoundError(key)
        return obj.data

    def delete(self, *, key: str) -> None:
        self._objects.pop(key, None)

    def presign_get(self, *, key: str, expires_in_seconds: int) -> str:
        # Fake "signed" URL — good enough for tests/local dev, which never
        # actually fetch it over HTTP. Encodes an expiry so tests can
        # assert on it if needed.
        expires_at = int(time.time()) + expires_in_seconds
        return f"memory://{key}?expires_at={expires_at}"


_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _client
    if _client is None:
        settings = get_settings()
        if settings.r2_account_id and settings.r2_bucket_name:
            _client = R2StorageClient()
        else:
            _client = InMemoryStorageClient()
    return _client


def reset_storage_client_for_tests() -> None:
    """Test-only helper — forces the next get_storage_client() call to
    re-evaluate config and build a fresh in-memory client."""
    global _client
    _client = None


__all__ = [
    "InMemoryStorageClient",
    "ObjectNotFoundError",
    "R2StorageClient",
    "StorageClient",
    "get_storage_client",
    "reset_storage_client_for_tests",
    "io",
]
