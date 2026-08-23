from bson import ObjectId

from app.shared.db import get_db


async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


async def _set_tier(user_id: str, tier: str) -> None:
    db = get_db()
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"tier": tier}})


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_premium_user_cannot_access_routines_or_life(client):
    token, user_id = await _register(client, "premium@example.com")
    await _set_tier(user_id, "premium")

    routine_resp = await client.post(
        "/v1/litheral/routines",
        json={"label": "Gym", "days": [1, 3], "start_time": "18:00", "end_time": "19:00"},
        headers=_auth(token),
    )
    assert routine_resp.status_code == 403
    assert routine_resp.json()["error_code"] == "upgrade_required"

    life_resp = await client.post("/v1/litheral/life/generate", headers=_auth(token))
    assert life_resp.status_code == 403


async def test_pro_user_generates_life_schedule_with_routines(client):
    token, user_id = await _register(client, "pro@example.com")
    await _set_tier(user_id, "pro")

    await client.post(
        "/v1/timetable",
        json={"subject": "CS", "day_of_week": 0, "start_time": "09:00", "end_time": "12:00"},
        headers=_auth(token),
    )
    routine_resp = await client.post(
        "/v1/litheral/routines",
        json={"label": "Gym", "days": [0], "start_time": "18:00", "end_time": "19:00", "is_flexible": True},
        headers=_auth(token),
    )
    assert routine_resp.status_code == 201

    gen_resp = await client.post("/v1/litheral/life/generate", headers=_auth(token))
    assert gen_resp.status_code == 201
    blocks = gen_resp.json()
    source_types = {b["source_type"] for b in blocks}
    assert "class" in source_types
    assert "routine" in source_types

    listed = await client.get("/v1/litheral/life", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == len(blocks)


async def test_conflicting_fixed_routine_is_flagged_in_response(client):
    token, user_id = await _register(client, "pro2@example.com")
    await _set_tier(user_id, "pro")

    await client.post(
        "/v1/timetable",
        json={"subject": "CS", "day_of_week": 2, "start_time": "09:00", "end_time": "11:00"},
        headers=_auth(token),
    )
    await client.post(
        "/v1/litheral/routines",
        json={"label": "Church", "days": [2], "start_time": "09:00", "end_time": "10:00", "is_flexible": False},
        headers=_auth(token),
    )

    gen_resp = await client.post("/v1/litheral/life/generate", headers=_auth(token))
    routine_block = next(b for b in gen_resp.json() if b["source_type"] == "routine")
    assert routine_block["conflict_flag"] is True


async def test_life_adjust_is_capped(client, monkeypatch):
    from app.shared.config import get_settings

    monkeypatch.setenv("AI_CAP_LIFE_ADJUST_MONTHLY", "1")
    get_settings.cache_clear()

    token, user_id = await _register(client, "pro3@example.com")
    await _set_tier(user_id, "pro")

    await client.post("/v1/litheral/life/generate", headers=_auth(token))

    first_adjust = await client.post("/v1/litheral/life/adjust", headers=_auth(token))
    assert first_adjust.status_code == 200

    second_adjust = await client.post("/v1/litheral/life/adjust", headers=_auth(token))
    assert second_adjust.status_code == 429
    assert second_adjust.json()["error_code"] == "cap_reached"

    get_settings.cache_clear()


async def test_routines_are_owner_isolated(client):
    token_a, user_a = await _register(client, "a@example.com")
    await _set_tier(user_a, "pro")
    token_b, user_b = await _register(client, "b@example.com")
    await _set_tier(user_b, "pro")

    create_resp = await client.post(
        "/v1/litheral/routines",
        json={"label": "Sleep", "days": [0], "start_time": "23:00", "end_time": "23:59"},
        headers=_auth(token_a),
    )
    routine_id = create_resp.json()["id"]

    delete_by_b = await client.delete(f"/v1/litheral/routines/{routine_id}", headers=_auth(token_b))
    assert delete_by_b.status_code == 404
