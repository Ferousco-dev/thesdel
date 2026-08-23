from app.shared.db import get_db


async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _capture_push_jobs(monkeypatch):
    """Stubs `enqueue_push_to_user` the same way tests/test_auth_verification.py
    stubs the auth email enqueue helpers — captures calls instead of hitting
    a real ARQ pool/Redis connection."""
    calls: list[dict] = []

    async def _fake_enqueue(*, user_id: str, title: str, body: str, data=None) -> None:
        calls.append({"user_id": user_id, "title": title, "body": body, "data": data or {}})

    import app.notifications.service as notifications_service_module

    monkeypatch.setattr(notifications_service_module, "enqueue_push_to_user", _fake_enqueue)
    return calls


# -- device token registration ------------------------------------------


async def test_register_device_is_idempotent(client):
    token, _ = await _register(client, "device@example.com")

    first = await client.post(
        "/v1/notifications/devices",
        json={"token": "fcm-token-abc", "platform": "ios"},
        headers=_auth(token),
    )
    assert first.status_code == 201

    second = await client.post(
        "/v1/notifications/devices",
        json={"token": "fcm-token-abc", "platform": "ios"},
        headers=_auth(token),
    )
    assert second.status_code == 201

    db = get_db()
    count = await db.device_tokens.count_documents({"token": "fcm-token-abc"})
    assert count == 1


async def test_user_can_only_unregister_own_token(client):
    token_a, _ = await _register(client, "owner@example.com")
    token_b, _ = await _register(client, "other@example.com")

    await client.post(
        "/v1/notifications/devices",
        json={"token": "fcm-token-owner", "platform": "android"},
        headers=_auth(token_a),
    )

    # Someone else's token: not found, not deleted.
    forbidden_delete = await client.delete(
        "/v1/notifications/devices/fcm-token-owner", headers=_auth(token_b)
    )
    assert forbidden_delete.status_code == 404

    db = get_db()
    assert await db.device_tokens.find_one({"token": "fcm-token-owner"}) is not None

    own_delete = await client.delete(
        "/v1/notifications/devices/fcm-token-owner", headers=_auth(token_a)
    )
    assert own_delete.status_code == 204
    assert await db.device_tokens.find_one({"token": "fcm-token-owner"}) is None


# -- announcement fan-out -------------------------------------------------


async def test_announcement_post_notifies_class_members_excluding_poster(client, monkeypatch):
    calls = _capture_push_jobs(monkeypatch)

    rep_token, rep_id = await _register(client, "rep@example.com")
    create_resp = await client.post(
        "/v1/classes", json={"name": "CS 101"}, headers=_auth(rep_token)
    )
    class_id = create_resp.json()["id"]
    join_code = create_resp.json()["join_code"]

    member_token, member_id = await _register(client, "member@example.com")
    await client.post(
        "/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token)
    )

    post_resp = await client.post(
        f"/v1/classes/{class_id}/announcements",
        json={"content": "First day of class"},
        headers=_auth(rep_token),
    )
    assert post_resp.status_code == 201

    assert len(calls) == 1
    assert calls[0]["user_id"] == member_id
    assert not any(c["user_id"] == rep_id for c in calls)


async def test_dedup_guard_prevents_duplicate_send_for_same_trigger(client, monkeypatch):
    """Exercises NotificationService._dedup_or_skip directly — the
    Redis SETNX-with-TTL mechanism docs/ARCHITECTURE.md §7/§8 requires
    ("notification jobs ... are still deduplicated to avoid spamming
    users"). The first call for a given {notification_type, source_id}
    proceeds; a second call for the same key within the TTL window is
    skipped."""
    from app.notifications.service import NotificationService
    from app.shared.db import get_db
    from app.shared.redis_client import get_redis

    notif = NotificationService(get_db(), get_redis())
    first = await notif._dedup_or_skip("announcement_new", "fixed-announcement-id")
    second = await notif._dedup_or_skip("announcement_new", "fixed-announcement-id")
    assert first is True
    assert second is False

    # A different source_id is a distinct dedup key — not suppressed.
    third = await notif._dedup_or_skip("announcement_new", "a-different-announcement-id")
    assert third is True


# -- life-schedule conflict alert -----------------------------------------


async def test_life_conflict_enqueues_exactly_one_push_regardless_of_block_count(
    client, monkeypatch
):
    calls = _capture_push_jobs(monkeypatch)

    from bson import ObjectId

    token, user_id = await _register(client, "pro@example.com")
    db = get_db()
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"tier": "pro"}})

    # Two overlapping fixed timetable entries against a routine so more
    # than one resulting block is flagged conflicting.
    await client.post(
        "/v1/timetable",
        json={"subject": "CS", "day_of_week": 0, "start_time": "09:00", "end_time": "11:00"},
        headers=_auth(token),
    )
    await client.post(
        "/v1/litheral/routines",
        json={
            "label": "Gym",
            "days": [0],
            "start_time": "09:30",
            "end_time": "10:30",
            "is_flexible": False,
        },
        headers=_auth(token),
    )
    await client.post(
        "/v1/litheral/routines",
        json={
            "label": "Call",
            "days": [0],
            "start_time": "10:00",
            "end_time": "10:45",
            "is_flexible": False,
        },
        headers=_auth(token),
    )

    gen_resp = await client.post("/v1/litheral/life/generate", headers=_auth(token))
    assert gen_resp.status_code == 201
    blocks = gen_resp.json()
    assert sum(1 for b in blocks if b["conflict_flag"]) >= 1

    conflict_calls = [c for c in calls if c["data"].get("type") == "life_conflict"]
    assert len(conflict_calls) == 1
    assert conflict_calls[0]["user_id"] == user_id
