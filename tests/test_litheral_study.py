from bson import ObjectId

from app.shared.db import get_db


async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


async def _promote_to_premium(user_id: str) -> None:
    # No billing module yet (ADR-007 is open) — directly flipping tier in
    # the test DB is the test-only equivalent of a verified webhook.
    db = get_db()
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"tier": "premium"}})


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _add_timetable_entry(client, token, subject, day, start, end):
    resp = await client.post(
        "/v1/timetable",
        json={"subject": subject, "day_of_week": day, "start_time": start, "end_time": end},
        headers=_auth(token),
    )
    assert resp.status_code == 201


async def test_free_user_cannot_generate_study_plan(client):
    token, _ = await _register(client, "free@example.com")
    resp = await client.post("/v1/litheral/study/generate", json={"subjects": []}, headers=_auth(token))
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "upgrade_required"


async def test_premium_user_generates_study_plan_around_classes(client):
    token, user_id = await _register(client, "premium@example.com")
    await _promote_to_premium(user_id)

    await _add_timetable_entry(client, token, "Chemistry", 0, "09:00", "17:00")

    resp = await client.post(
        "/v1/litheral/study/generate",
        json={"subjects": [{"subject": "Chemistry", "priority": 3}]},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    blocks = resp.json()
    assert len(blocks) > 0
    for block in blocks:
        if block["day_of_week"] == 0:
            assert block["end_time"] <= "09:00" or block["start_time"] >= "17:00"

    listed = await client.get("/v1/litheral/study", headers=_auth(token))
    assert listed.status_code == 200
    assert len(listed.json()) == len(blocks)


async def test_generate_with_no_subjects_derives_from_timetable(client):
    token, user_id = await _register(client, "premium2@example.com")
    await _promote_to_premium(user_id)
    await _add_timetable_entry(client, token, "Biology", 1, "10:00", "11:00")

    resp = await client.post("/v1/litheral/study/generate", json={"subjects": []}, headers=_auth(token))
    assert resp.status_code == 201
    subjects = {b["subject"] for b in resp.json()}
    assert subjects == {"Biology"}


async def test_regenerate_is_capped_and_reports_remaining(client, monkeypatch):
    from app.shared.config import get_settings

    monkeypatch.setenv("AI_CAP_STUDY_REGENERATE_MONTHLY", "2")
    get_settings.cache_clear()

    token, user_id = await _register(client, "premium3@example.com")
    await _promote_to_premium(user_id)

    gen = await client.post(
        "/v1/litheral/study/generate",
        json={"subjects": [{"subject": "Math"}]},
        headers=_auth(token),
    )
    block_id = gen.json()[0]["id"]

    first = await client.post(f"/v1/litheral/study/{block_id}/regenerate", headers=_auth(token))
    assert first.status_code == 200
    assert first.json()["remaining_regenerations"] == 1
    new_block_id = first.json()["block"]["id"]

    second = await client.post(f"/v1/litheral/study/{new_block_id}/regenerate", headers=_auth(token))
    assert second.status_code == 200
    assert second.json()["remaining_regenerations"] == 0
    newest_block_id = second.json()["block"]["id"]

    third = await client.post(f"/v1/litheral/study/{newest_block_id}/regenerate", headers=_auth(token))
    assert third.status_code == 429
    assert third.json()["error_code"] == "cap_reached"

    get_settings.cache_clear()


async def test_usage_endpoint_reflects_regenerate_count(client, monkeypatch):
    from app.shared.config import get_settings

    monkeypatch.setenv("AI_CAP_STUDY_REGENERATE_MONTHLY", "5")
    get_settings.cache_clear()

    token, user_id = await _register(client, "premium4@example.com")
    await _promote_to_premium(user_id)

    gen = await client.post(
        "/v1/litheral/study/generate",
        json={"subjects": [{"subject": "Math"}]},
        headers=_auth(token),
    )
    block_id = gen.json()[0]["id"]
    await client.post(f"/v1/litheral/study/{block_id}/regenerate", headers=_auth(token))

    usage = await client.get("/v1/usage/ai", headers=_auth(token))
    assert usage.status_code == 200
    study_cap = next(c for c in usage.json()["caps"] if c["feature"] == "study_regenerate")
    assert study_cap["used"] == 1
    assert study_cap["remaining"] == 4

    get_settings.cache_clear()


async def test_cannot_regenerate_another_users_block(client):
    token_a, user_a = await _register(client, "owner@example.com")
    await _promote_to_premium(user_a)
    gen = await client.post(
        "/v1/litheral/study/generate",
        json={"subjects": [{"subject": "Math"}]},
        headers=_auth(token_a),
    )
    block_id = gen.json()[0]["id"]

    token_b, user_b = await _register(client, "other@example.com")
    await _promote_to_premium(user_b)
    resp = await client.post(f"/v1/litheral/study/{block_id}/regenerate", headers=_auth(token_b))
    assert resp.status_code == 404
