async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_class_makes_creator_rep(client):
    token, _ = await _register(client, "rep@example.com")
    resp = await client.post("/v1/classes", json={"name": "CS 101"}, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["member_count"] == 1
    assert len(body["join_code"]) == 7


async def test_join_class_by_code(client):
    rep_token, _ = await _register(client, "rep2@example.com")
    create_resp = await client.post("/v1/classes", json={"name": "Physics"}, headers=_auth(rep_token))
    join_code = create_resp.json()["join_code"]
    class_id = create_resp.json()["id"]

    member_token, _ = await _register(client, "member@example.com")
    join_resp = await client.post(
        "/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token)
    )
    assert join_resp.status_code == 200
    assert join_resp.json()["role"] == "member"

    get_resp = await client.get(f"/v1/classes/{class_id}", headers=_auth(member_token))
    assert get_resp.status_code == 200
    assert get_resp.json()["member_count"] == 2


async def test_join_class_is_idempotent(client):
    rep_token, _ = await _register(client, "rep3@example.com")
    create_resp = await client.post("/v1/classes", json={"name": "Chem"}, headers=_auth(rep_token))
    join_code = create_resp.json()["join_code"]

    member_token, _ = await _register(client, "member2@example.com")
    first = await client.post("/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token))
    second = await client.post("/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token))
    assert first.status_code == 200
    assert second.status_code == 200

    class_id = create_resp.json()["id"]
    get_resp = await client.get(f"/v1/classes/{class_id}", headers=_auth(rep_token))
    assert get_resp.json()["member_count"] == 2  # not 3 — duplicate join didn't double-count


async def test_non_member_cannot_view_class(client):
    rep_token, _ = await _register(client, "rep4@example.com")
    create_resp = await client.post("/v1/classes", json={"name": "History"}, headers=_auth(rep_token))
    class_id = create_resp.json()["id"]

    outsider_token, _ = await _register(client, "outsider@example.com")
    resp = await client.get(f"/v1/classes/{class_id}", headers=_auth(outsider_token))
    assert resp.status_code == 404  # not 403 — existence not revealed to non-members


async def test_only_rep_can_post_class_timetable(client):
    rep_token, _ = await _register(client, "rep5@example.com")
    create_resp = await client.post("/v1/classes", json={"name": "Bio"}, headers=_auth(rep_token))
    class_id = create_resp.json()["id"]
    join_code = create_resp.json()["join_code"]

    member_token, _ = await _register(client, "member3@example.com")
    await client.post("/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token))

    entry = {
        "subject": "Cell Biology",
        "day_of_week": 1,
        "start_time": "09:00",
        "end_time": "10:00",
    }
    member_attempt = await client.post(
        f"/v1/timetable/class/{class_id}", json=entry, headers=_auth(member_token)
    )
    assert member_attempt.status_code == 403
    assert member_attempt.json()["error_code"] == "forbidden"

    rep_attempt = await client.post(
        f"/v1/timetable/class/{class_id}", json=entry, headers=_auth(rep_token)
    )
    assert rep_attempt.status_code == 201

    member_read = await client.get(f"/v1/timetable/class/{class_id}", headers=_auth(member_token))
    assert member_read.status_code == 200
    assert len(member_read.json()) == 1


async def test_personal_timetable_crud_and_isolation(client):
    token_a, _ = await _register(client, "a@example.com")
    token_b, _ = await _register(client, "b@example.com")

    create_resp = await client.post(
        "/v1/timetable",
        json={"subject": "Algebra", "day_of_week": 2, "start_time": "08:00", "end_time": "09:00"},
        headers=_auth(token_a),
    )
    assert create_resp.status_code == 201
    entry_id = create_resp.json()["id"]

    # user B cannot see or modify user A's personal entry
    list_b = await client.get("/v1/timetable", headers=_auth(token_b))
    assert list_b.json() == []

    update_by_b = await client.patch(
        f"/v1/timetable/{entry_id}", json={"subject": "Hacked"}, headers=_auth(token_b)
    )
    assert update_by_b.status_code == 404

    delete_by_b = await client.delete(f"/v1/timetable/{entry_id}", headers=_auth(token_b))
    assert delete_by_b.status_code == 404

    update_by_a = await client.patch(
        f"/v1/timetable/{entry_id}", json={"subject": "Calculus"}, headers=_auth(token_a)
    )
    assert update_by_a.status_code == 200
    assert update_by_a.json()["subject"] == "Calculus"


async def test_invalid_time_range_rejected(client):
    token, _ = await _register(client, "timeorder@example.com")
    resp = await client.post(
        "/v1/timetable",
        json={"subject": "X", "day_of_week": 0, "start_time": "10:00", "end_time": "09:00"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_announcements_feed_pinned_first_and_rep_only_post(client):
    rep_token, _ = await _register(client, "rep6@example.com")
    create_resp = await client.post("/v1/classes", json={"name": "Art"}, headers=_auth(rep_token))
    class_id = create_resp.json()["id"]
    join_code = create_resp.json()["join_code"]

    member_token, _ = await _register(client, "member4@example.com")
    await client.post("/v1/classes/join", json={"join_code": join_code}, headers=_auth(member_token))

    member_post = await client.post(
        f"/v1/classes/{class_id}/announcements", json={"content": "hi"}, headers=_auth(member_token)
    )
    assert member_post.status_code == 403

    a1 = await client.post(
        f"/v1/classes/{class_id}/announcements", json={"content": "first"}, headers=_auth(rep_token)
    )
    a2 = await client.post(
        f"/v1/classes/{class_id}/announcements", json={"content": "pin me"}, headers=_auth(rep_token)
    )
    assert a1.status_code == 201 and a2.status_code == 201

    pin_resp = await client.patch(
        f"/v1/classes/{class_id}/announcements/{a2.json()['id']}",
        json={"pinned": True},
        headers=_auth(rep_token),
    )
    assert pin_resp.status_code == 200
    assert pin_resp.json()["pinned"] is True

    feed = await client.get(f"/v1/classes/{class_id}/announcements", headers=_auth(member_token))
    assert feed.status_code == 200
    items = feed.json()["items"]
    assert items[0]["content"] == "pin me"
    assert items[0]["pinned"] is True
