from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.shared.db import ensure_indexes, get_db
from app.shared.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.streaks.repository import normalize_pair
from app.streaks.service import StreakService


async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -- invite / accept flow -----------------------------------------------------


async def test_invite_creates_pending_pair_normalized(client):
    _, user_a = await _register(client, "streak_a1@example.com")
    _, user_b = await _register(client, "streak_b1@example.com")

    service = StreakService(get_db())
    streak = await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    assert streak.status == "pending"
    expected_a, expected_b = normalize_pair(ObjectId(user_a), ObjectId(user_b))
    assert streak.user_a == str(expected_a)
    assert streak.user_b == str(expected_b)


async def test_invite_rejects_self(client):
    _, user_a = await _register(client, "streak_self@example.com")
    service = StreakService(get_db())
    with pytest.raises(ValidationAppError):
        await service.invite(current_user_id=user_a, invitee_user_id=user_a)


async def test_invite_rejects_nonexistent_user(client):
    _, user_a = await _register(client, "streak_a2@example.com")
    service = StreakService(get_db())
    with pytest.raises(NotFoundError):
        await service.invite(current_user_id=user_a, invitee_user_id=str(ObjectId()))


async def test_duplicate_invite_is_idempotent(client):
    _, user_a = await _register(client, "streak_a3@example.com")
    _, user_b = await _register(client, "streak_b3@example.com")
    await ensure_indexes()

    service = StreakService(get_db())
    first = await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    second = await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    assert first.id == second.id
    assert second.status == "pending"

    db = get_db()
    count = await db.partner_streaks.count_documents({})
    assert count == 1


async def test_only_invitee_can_accept_inviter_rejected(client):
    _, user_a = await _register(client, "streak_a4@example.com")
    _, user_b = await _register(client, "streak_b4@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    # The inviter (A) trying to "accept" their own invite must be rejected.
    with pytest.raises(ForbiddenError):
        await service.accept(current_user_id=user_a, inviter_user_id=user_b)

    # The actual invitee (B) can accept.
    accepted = await service.accept(current_user_id=user_b, inviter_user_id=user_a)
    assert accepted.status == "active"
    assert accepted.last_interaction_at is not None


async def test_accept_nonexistent_invite_raises(client):
    _, user_a = await _register(client, "streak_a5@example.com")
    service = StreakService(get_db())
    with pytest.raises(NotFoundError):
        await service.accept(current_user_id=user_a, inviter_user_id=str(ObjectId()))


async def test_duplicate_accept_is_idempotent(client):
    _, user_a = await _register(client, "streak_a6@example.com")
    _, user_b = await _register(client, "streak_b6@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    first = await service.accept(current_user_id=user_b, inviter_user_id=user_a)
    second = await service.accept(current_user_id=user_b, inviter_user_id=user_a)

    assert first.status == "active"
    assert second.status == "active"
    assert first.id == second.id


# -- check-in authorization / behavior ----------------------------------------


async def test_check_in_requires_membership(client):
    _, user_a = await _register(client, "streak_a7@example.com")
    _, user_b = await _register(client, "streak_b7@example.com")
    _, user_c = await _register(client, "streak_c7@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    await service.accept(current_user_id=user_b, inviter_user_id=user_a)

    with pytest.raises(NotFoundError):
        # C has no streak with A at all.
        await service.check_in(current_user_id=user_c, partner_user_id=user_a)


async def test_check_in_endpoint_requires_auth(client):
    resp = await client.post("/v1/streaks/check-in", json={"partner_user_id": str(ObjectId())})
    assert resp.status_code == 401


async def test_check_in_rejected_while_pending(client):
    _, user_a = await _register(client, "streak_a8@example.com")
    _, user_b = await _register(client, "streak_b8@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    with pytest.raises(ConflictError):
        await service.check_in(current_user_id=user_a, partner_user_id=user_b)


async def test_check_in_increments_streak_and_is_idempotent_same_day(client):
    _, user_a = await _register(client, "streak_a9@example.com")
    _, user_b = await _register(client, "streak_b9@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    await service.accept(current_user_id=user_b, inviter_user_id=user_a)

    # Acceptance itself stamps day 1 (current_streak=1, last_interaction_at
    # = now) — see docs/DECISIONS.md ADR-009. A same-day check-in
    # afterwards is therefore an idempotent no-op, not a double-increment.
    result = await service.check_in(current_user_id=user_a, partner_user_id=user_b)
    assert result.streak.current_streak == 1
    assert result.already_checked_in_today is True

    result_again = await service.check_in(current_user_id=user_b, partner_user_id=user_a)
    assert result_again.streak.current_streak == 1
    assert result_again.already_checked_in_today is True


async def test_check_in_increments_across_days(client):
    _, user_a = await _register(client, "streak_a10@example.com")
    _, user_b = await _register(client, "streak_b10@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    await service.accept(current_user_id=user_b, inviter_user_id=user_a)
    await service.check_in(current_user_id=user_a, partner_user_id=user_b)

    # Simulate "yesterday" by backdating last_interaction_at within the
    # stale window (24h ago — not stale, should just increment).
    db = get_db()
    doc = await db.partner_streaks.find_one({})
    yesterday = datetime.now(UTC) - timedelta(hours=24)
    await db.partner_streaks.update_one(
        {"_id": doc["_id"]}, {"$set": {"last_interaction_at": yesterday}}
    )

    result = await service.check_in(current_user_id=user_a, partner_user_id=user_b)
    assert result.streak.current_streak == 2


async def test_check_in_resets_after_stale_window(client):
    _, user_a = await _register(client, "streak_a11@example.com")
    _, user_b = await _register(client, "streak_b11@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)
    await service.accept(current_user_id=user_b, inviter_user_id=user_a)
    await service.check_in(current_user_id=user_a, partner_user_id=user_b)

    db = get_db()
    doc = await db.partner_streaks.find_one({})
    assert doc["current_streak"] == 1

    # Backdate beyond the 48h stale window.
    stale_time = datetime.now(UTC) - timedelta(hours=72)
    await db.partner_streaks.update_one(
        {"_id": doc["_id"]}, {"$set": {"last_interaction_at": stale_time}}
    )

    # A lazy read (list_my_streaks) should already reflect the reset without
    # any write happening.
    streaks = await service.list_my_streaks(current_user_id=user_a)
    assert streaks[0].current_streak == 0
    persisted = await db.partner_streaks.find_one({"_id": doc["_id"]})
    assert persisted["current_streak"] == 1  # read-only view, not yet persisted

    # A new check-in after staleness resets to 1, not 2.
    result = await service.check_in(current_user_id=user_b, partner_user_id=user_a)
    assert result.streak.current_streak == 1


# -- unique index / normalization ---------------------------------------------


async def test_unique_index_enforced_regardless_of_argument_order(client):
    _, user_a = await _register(client, "streak_a12@example.com")
    _, user_b = await _register(client, "streak_b12@example.com")
    await ensure_indexes()

    db = get_db()
    a_oid, b_oid = normalize_pair(ObjectId(user_a), ObjectId(user_b))
    await db.partner_streaks.insert_one(
        {
            "user_a": a_oid,
            "user_b": b_oid,
            "invited_by": a_oid,
            "current_streak": 0,
            "last_interaction_at": None,
            "status": "pending",
        }
    )

    # Attempting to insert the same normalized pair again (even if a caller
    # somehow bypassed the service's normalization and passed fields in
    # reversed order) violates the unique index once normalized correctly.
    with pytest.raises(DuplicateKeyError):
        await db.partner_streaks.insert_one(
            {
                "user_a": a_oid,
                "user_b": b_oid,
                "invited_by": b_oid,
                "current_streak": 0,
                "last_interaction_at": None,
                "status": "pending",
            }
        )


async def test_normalize_pair_is_order_independent(client):
    x = ObjectId()
    y = ObjectId()
    a1, b1 = normalize_pair(x, y)
    a2, b2 = normalize_pair(y, x)
    assert (a1, b1) == (a2, b2)
    assert str(a1) < str(b1)


# -- reads / authorization -----------------------------------------------------


async def test_list_my_streaks_requires_auth(client):
    resp = await client.get("/v1/streaks/me")
    assert resp.status_code == 401


async def test_list_my_streaks_returns_only_own_pairs(client):
    _, user_a = await _register(client, "streak_a13@example.com")
    _, user_b = await _register(client, "streak_b13@example.com")
    _, user_c = await _register(client, "streak_c13@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    a_streaks = await service.list_my_streaks(current_user_id=user_a)
    c_streaks = await service.list_my_streaks(current_user_id=user_c)

    assert len(a_streaks) == 1
    assert len(c_streaks) == 0


async def test_get_with_partner_not_found_for_non_member(client):
    _, user_a = await _register(client, "streak_a14@example.com")
    _, user_b = await _register(client, "streak_b14@example.com")
    _, user_c = await _register(client, "streak_c14@example.com")

    service = StreakService(get_db())
    await service.invite(current_user_id=user_a, invitee_user_id=user_b)

    with pytest.raises(NotFoundError):
        await service.get_with_partner(current_user_id=user_c, partner_user_id=user_a)


# -- HTTP-level end-to-end smoke ------------------------------------------------


async def test_invite_accept_check_in_via_http(client):
    token_a, user_a = await _register(client, "streak_http_a@example.com")
    token_b, user_b = await _register(client, "streak_http_b@example.com")

    resp = await client.post(
        "/v1/streaks/invite", json={"invitee_user_id": user_b}, headers=_auth(token_a)
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    # Inviter cannot accept their own invite over HTTP either.
    resp_bad = await client.post(
        "/v1/streaks/accept", json={"inviter_user_id": user_b}, headers=_auth(token_a)
    )
    assert resp_bad.status_code == 403

    resp_accept = await client.post(
        "/v1/streaks/accept", json={"inviter_user_id": user_a}, headers=_auth(token_b)
    )
    assert resp_accept.status_code == 200
    assert resp_accept.json()["status"] == "active"

    resp_checkin = await client.post(
        "/v1/streaks/check-in", json={"partner_user_id": user_b}, headers=_auth(token_a)
    )
    assert resp_checkin.status_code == 200
    assert resp_checkin.json()["streak"]["current_streak"] == 1
