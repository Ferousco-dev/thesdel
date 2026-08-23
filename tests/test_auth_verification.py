from datetime import UTC, datetime, timedelta

from app.shared.db import get_db


async def _register(client, email="student@example.com", password="correct-horse-1"):
    return await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Ada"},
    )


def _capture_email_jobs(monkeypatch):
    """Stubs the enqueue helpers app/auth/service.py calls, mirroring the
    existing fakeredis-style infra stubbing in tests/conftest.py — captures
    calls instead of hitting a real ARQ pool/Redis connection."""
    calls: list[dict] = []

    async def _fake_enqueue_verification(*, user_id: str, email: str, token: str) -> None:
        calls.append({"kind": "verification", "user_id": user_id, "email": email, "token": token})

    async def _fake_enqueue_reset(*, user_id: str, email: str, token: str) -> None:
        calls.append({"kind": "password_reset", "user_id": user_id, "email": email, "token": token})

    import app.auth.service as service_module

    monkeypatch.setattr(service_module, "enqueue_email_verification", _fake_enqueue_verification)
    monkeypatch.setattr(service_module, "enqueue_password_reset_email", _fake_enqueue_reset)
    return calls


async def _expire_token(token_hash_purpose_email: str, purpose: str) -> None:
    """Back-dates the matching auth_tokens document's expires_at so it now
    reads as expired."""
    db = get_db()
    await db.auth_tokens.update_many(
        {"purpose": purpose},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(minutes=1)}},
    )


async def test_register_enqueues_verification_email(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    resp = await _register(client)
    assert resp.status_code == 201

    verification_calls = [c for c in calls if c["kind"] == "verification"]
    assert len(verification_calls) == 1
    assert verification_calls[0]["email"] == "student@example.com"


async def test_verify_email_valid_token_verifies_and_is_idempotent(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    token = calls[0]["token"]

    first = await client.post("/v1/auth/verify-email", json={"token": token})
    assert first.status_code == 200

    db = get_db()
    user = await db.users.find_one({"email": "student@example.com"})
    assert user["email_verified_at"] is not None

    # Idempotent-success: verifying again with the same (now-used) token
    # must not error, since the account is already verified.
    second = await client.post("/v1/auth/verify-email", json={"token": token})
    assert second.status_code == 200


async def test_verify_email_wrong_token_rejected(client):
    resp = await client.post("/v1/auth/verify-email", json={"token": "not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "token_invalid"


async def test_verify_email_expired_token_rejected(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    token = calls[0]["token"]

    await _expire_token(token, "email_verification")

    resp = await client.post("/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "token_expired"


async def test_resend_verification_enqueues_new_token_and_is_generic(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    assert len(calls) == 1

    resp = await client.post(
        "/v1/auth/resend-verification", json={"email": "student@example.com"}
    )
    assert resp.status_code == 200
    verification_calls = [c for c in calls if c["kind"] == "verification"]
    assert len(verification_calls) == 2

    # Unknown email: same generic response, no enumeration signal.
    unknown_resp = await client.post(
        "/v1/auth/resend-verification", json={"email": "nobody@example.com"}
    )
    assert unknown_resp.status_code == 200
    assert unknown_resp.json() == resp.json()


async def test_password_reset_flow_updates_password_and_revokes_all_sessions(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    reg = await _register(client)
    old_refresh_token = reg.json()["refresh_token"]

    resp = await client.post(
        "/v1/auth/password-reset/request", json={"email": "student@example.com"}
    )
    assert resp.status_code == 200

    reset_calls = [c for c in calls if c["kind"] == "password_reset"]
    assert len(reset_calls) == 1
    token = reset_calls[0]["token"]

    confirm = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-password-1"},
    )
    assert confirm.status_code == 200

    # Old session is revoked — the pre-reset refresh token must no longer work.
    refresh_after_reset = await client.post(
        "/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refresh_after_reset.status_code == 401

    # New password logs in; old password does not.
    login_new = await client.post(
        "/v1/auth/login",
        json={"email": "student@example.com", "password": "brand-new-password-1"},
    )
    assert login_new.status_code == 200

    login_old = await client.post(
        "/v1/auth/login",
        json={"email": "student@example.com", "password": "correct-horse-1"},
    )
    assert login_old.status_code == 401


async def test_password_reset_nonexistent_email_returns_generic_success(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    resp = await client.post(
        "/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    assert not any(c["kind"] == "password_reset" for c in calls)


async def test_password_reset_expired_token_rejected(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "student@example.com"})
    token = [c for c in calls if c["kind"] == "password_reset"][0]["token"]

    await _expire_token(token, "password_reset")

    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "another-new-password-1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "token_expired"


async def test_password_reset_reused_token_rejected(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "student@example.com"})
    token = [c for c in calls if c["kind"] == "password_reset"][0]["token"]

    first = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "another-new-password-1"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "yet-another-password-2"},
    )
    assert second.status_code == 401
    assert second.json()["error_code"] == "token_invalid"


async def test_password_reset_tampered_token_rejected(client, monkeypatch):
    calls = _capture_email_jobs(monkeypatch)
    await _register(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "student@example.com"})
    token = [c for c in calls if c["kind"] == "password_reset"][0]["token"]

    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    resp = await client.post(
        "/v1/auth/password-reset/confirm",
        json={"token": tampered, "new_password": "another-new-password-1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "token_invalid"
