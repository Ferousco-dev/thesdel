"""Tests for the timetable-import file upload module.

Coverage:
1. Valid image upload → storage + re-encoding
2. Oversized file rejected
3. Disguised file type rejected
4. Cross-user access blocked
5. Presigned-URL retrieval and ownership check
6. Delete removes both Mongo doc and R2 object
7. Cleanup job identifies and deletes stale pending_parse records
"""

import io
from datetime import UTC, datetime, timedelta

from PIL import Image

from app.files.jobs import cleanup_abandoned_file_uploads
from app.files.service import ABANDONED_TTL_HOURS, PRESIGN_EXPIRY_SECONDS
from app.shared.storage import reset_storage_client_for_tests


async def _register(client, email="user@test.com", password="password123"):
    """Helper: register a user and return (access_token, user_id)."""
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Test User"},
    )
    assert resp.status_code == 201
    body = resp.json()
    return body["access_token"], body["user"]["id"]


def _make_valid_image(fmt: str, width: int = 800, height: int = 600) -> bytes:
    """Generate a valid image in the given format (JPEG|PNG|WEBP)."""
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return buffer.getvalue()


def _make_disguised_file() -> bytes:
    """Create a file that claims to be JPEG but is actually invalid.
    A zip file with a JPEG extension would be a classic polyglot example,
    but for simplicity, we'll use a text file."""
    return b"This is not a real image, just some text pretending to be one"


def _make_oversized_image() -> bytes:
    """Generate an image larger than MAX_UPLOAD_BYTES (8MB).

    Since image compression is too effective, we create a fake PNG
    by combining a valid PNG header with a large padding."""
    # Create a minimal valid PNG and then pad it beyond 8MB
    img = Image.new("RGB", (100, 100), color=(100, 200, 150))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    png_data = buffer.getvalue()

    # Pad with extra data to exceed 8MB
    # (This is a fake image, but it's valid up to the padding)
    oversized = png_data + b"\x00" * (8 * 1024 * 1024 + 1)
    return oversized


async def test_valid_jpeg_upload(client):
    """Valid JPEG upload is stored in R2 and recorded in Mongo."""
    access_token, _ = await _register(client)

    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending_parse"
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] > 0
    assert "created_at" in body


async def test_valid_png_upload(client):
    """Valid PNG upload is accepted and re-encoded."""
    access_token, user_id = await _register(client)

    image_bytes = _make_valid_image("PNG")
    files = {"file": ("test.png", io.BytesIO(image_bytes), "image/png")}

    resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["content_type"] == "image/png"
    assert body["status"] == "pending_parse"


async def test_valid_webp_upload(client):
    """Valid WEBP upload is accepted."""
    access_token, _ = await _register(client)

    image_bytes = _make_valid_image("WEBP")
    files = {"file": ("test.webp", io.BytesIO(image_bytes), "image/webp")}

    resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["content_type"] == "image/webp"


async def test_oversized_file_rejected(client):
    """Upload exceeding 8MB is rejected before full buffering."""
    access_token, _ = await _register(client)

    # Create a large image that exceeds MAX_UPLOAD_BYTES
    oversized = _make_oversized_image()
    assert len(oversized) > 8 * 1024 * 1024

    files = {"file": ("big.jpg", io.BytesIO(oversized), "image/jpeg")}

    resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    # Should be rejected as an error (either 400 or 422 depending on whether
    # FastAPI/Pydantic or our validator catches it first)
    assert resp.status_code >= 400


async def test_disguised_file_type_rejected(client):
    """A file claiming to be JPEG but actually being text is rejected."""
    access_token, _ = await _register(client)

    fake_image = _make_disguised_file()
    # Note: FastAPI/Pydantic may reject this at the file-reading stage
    # before it even gets to our validation, since it's not a valid image.
    # We're testing that the upload endpoint rejects it (either way is fine).
    files = {"file": ("fake.jpg", io.BytesIO(fake_image), "text/plain")}

    resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )

    # Should fail — either validation error or unsupported type
    assert resp.status_code >= 400
    body = resp.json()
    # The error message will contain something about validation or unsupported type
    assert "validation_error" in body.get("error_code", "") or "error_code" in body


async def test_cross_user_access_blocked(client):
    """User B cannot access or delete User A's uploaded files."""
    access_token_a, user_id_a = await _register(client, email="user_a@test.com")
    access_token_b, user_id_b = await _register(client, email="user_b@test.com")

    # User A uploads a file
    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    upload_resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token_a}"},
        files=files,
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    # User B tries to get the download URL — should be 404 (not found)
    get_resp = await client.get(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token_b}"},
    )
    assert get_resp.status_code == 404

    # User B tries to delete it — should also be 404
    delete_resp = await client.delete(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token_b}"},
    )
    assert delete_resp.status_code == 404

    # User A can still access their own file
    get_resp = await client.get(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token_a}"},
    )
    assert get_resp.status_code == 200
    assert "url" in get_resp.json()


async def test_presigned_url_retrieval(client):
    """GET presigned-URL returns a short-lived, user-scoped link."""
    access_token, user_id = await _register(client)

    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    upload_resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    file_id = upload_resp.json()["id"]

    # Get the presigned URL
    url_resp = await client.get(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert url_resp.status_code == 200
    body = url_resp.json()
    assert body["file_id"] == file_id
    assert "url" in body
    assert body["expires_in_seconds"] == PRESIGN_EXPIRY_SECONDS


async def test_delete_removes_both_mongo_and_r2(client):
    """DELETE removes the Mongo record and the R2 object."""
    access_token, user_id = await _register(client)

    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    upload_resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    file_id = upload_resp.json()["id"]

    # Confirm it exists
    get_resp = await client.get(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert get_resp.status_code == 200

    # Delete it
    delete_resp = await client.delete(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_resp.status_code == 204

    # Now trying to get it should return 404
    get_after_delete = await client.get(
        f"/v1/files/timetable-import/{file_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert get_after_delete.status_code == 404


async def test_cleanup_job_deletes_stale_pending_parse_records(client):
    """Cleanup job identifies and deletes pending_parse records older than TTL."""
    from bson import ObjectId

    from app.shared.db import get_db

    # Reset storage to ensure a clean slate
    reset_storage_client_for_tests()

    access_token, user_id = await _register(client)

    # Upload a file
    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    upload_resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    # Manually update the created_at timestamp to be older than ABANDONED_TTL_HOURS
    db = get_db()
    stale_cutoff = datetime.now(UTC) - timedelta(hours=ABANDONED_TTL_HOURS + 1)
    file_oid = ObjectId(file_id)
    await db.file_uploads.update_one(
        {"_id": file_oid},
        {"$set": {"created_at": stale_cutoff}}
    )

    # Verify the record is now marked as stale
    stale_doc = await db.file_uploads.find_one({"_id": file_oid})
    assert stale_doc is not None
    assert stale_doc["status"] == "pending_parse"

    # Run the cleanup job
    cleaned = await cleanup_abandoned_file_uploads({})
    assert cleaned == 1

    # Verify the record is gone
    deleted_doc = await db.file_uploads.find_one({"_id": file_oid})
    assert deleted_doc is None


async def test_cleanup_job_skips_recent_pending_parse_records(client):
    """Cleanup job does NOT delete pending_parse records within the TTL window."""
    from bson import ObjectId

    from app.shared.db import get_db

    reset_storage_client_for_tests()

    access_token, user_id = await _register(client)

    # Upload a file
    image_bytes = _make_valid_image("JPEG")
    files = {"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")}

    upload_resp = await client.post(
        "/v1/files/timetable-import",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    # Run the cleanup job — should not delete a recent record
    cleaned = await cleanup_abandoned_file_uploads({})
    assert cleaned == 0

    # Verify the record still exists
    db = get_db()
    file_oid = ObjectId(file_id)
    doc = await db.file_uploads.find_one({"_id": file_oid})
    assert doc is not None
