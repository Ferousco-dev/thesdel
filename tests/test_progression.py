from datetime import UTC, date, datetime, timedelta

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.progression.service import ProgressionService, compute_rank
from app.shared.db import ensure_indexes, get_db
from app.shared.errors import NotFoundError


async def _register(client, email, password="correct-horse-1"):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Student"},
    )
    body = resp.json()
    return body["access_token"], body["user"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_badge(
    db,
    *,
    family="onboarding",
    name="Welcome",
    criteria_type="signup_completed",
    criteria_value=True,
):
    doc = {
        "family": family,
        "name": name,
        "criteria_type": criteria_type,
        "criteria_value": criteria_value,
    }
    result = await db.badges.insert_one(doc)
    return str(result.inserted_id)


# -- badge award idempotency / uniqueness --------------------------------


async def test_award_badge_is_idempotent(client):
    _, user_id = await _register(client, "badge1@example.com")
    db = get_db()
    await ensure_indexes()
    badge_id = await _make_badge(db)

    service = ProgressionService(db)
    first = await service.award_badge(user_id=user_id, badge_id=badge_id)
    second = await service.award_badge(user_id=user_id, badge_id=badge_id)

    assert first is True
    assert second is False  # duplicate award attempt is a no-op success, not an error

    count = await db.user_badges.count_documents(
        {"user_id": ObjectId(user_id), "badge_id": ObjectId(badge_id)}
    )
    assert count == 1


async def test_award_badge_nonexistent_badge_raises(client):
    _, user_id = await _register(client, "badge2@example.com")
    service = ProgressionService(get_db())
    with pytest.raises(NotFoundError):
        await service.award_badge(user_id=user_id, badge_id=str(ObjectId()))


async def test_unique_index_enforced_on_user_badges(client):
    _, user_id = await _register(client, "badge3@example.com")
    db = get_db()
    await ensure_indexes()
    badge_id = await _make_badge(db, name="Direct Insert Badge")

    doc = {
        "user_id": ObjectId(user_id),
        "badge_id": ObjectId(badge_id),
        "earned_at": datetime.now(UTC),
    }
    await db.user_badges.insert_one(doc)

    with pytest.raises(DuplicateKeyError):
        await db.user_badges.insert_one(doc)


async def test_evaluate_and_award_awards_matching_and_skips_unmet(client):
    _, user_id = await _register(client, "badge4@example.com")
    db = get_db()
    low = await _make_badge(
        db,
        family="study_litheral",
        name="First Session",
        criteria_type="study_sessions_completed",
        criteria_value=1,
    )
    high = await _make_badge(
        db,
        family="study_litheral",
        name="Ten Sessions",
        criteria_type="study_sessions_completed",
        criteria_value=10,
    )

    service = ProgressionService(db)
    awarded = await service.evaluate_and_award(
        user_id=user_id, criteria_type="study_sessions_completed", current_value=5
    )

    assert awarded == [low]
    assert high not in awarded

    # Re-running with the same value doesn't re-award (idempotent at the
    # evaluate layer, not just the repository layer).
    awarded_again = await service.evaluate_and_award(
        user_id=user_id, criteria_type="study_sessions_completed", current_value=5
    )
    assert awarded_again == []

    # Crossing the higher threshold awards the second badge, doesn't
    # duplicate the first.
    awarded_after = await service.evaluate_and_award(
        user_id=user_id, criteria_type="study_sessions_completed", current_value=12
    )
    assert awarded_after == [high]


# -- thesdel_score only increases -----------------------------------------


async def test_add_score_increments_and_persists(client):
    _, user_id = await _register(client, "score1@example.com")
    service = ProgressionService(get_db())

    new_score = await service.add_score(user_id=user_id, amount=50)
    assert new_score == 50

    new_score_2 = await service.add_score(user_id=user_id, amount=25)
    assert new_score_2 == 75


async def test_add_score_rejects_non_positive_amount(client):
    _, user_id = await _register(client, "score2@example.com")
    service = ProgressionService(get_db())

    with pytest.raises(ValueError):
        await service.add_score(user_id=user_id, amount=0)
    with pytest.raises(ValueError):
        await service.add_score(user_id=user_id, amount=-10)

    # Score untouched by the rejected calls.
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    assert user["thesdel_score"] == 0


async def test_add_score_updates_rank(client):
    _, user_id = await _register(client, "score3@example.com")
    service = ProgressionService(get_db())

    await service.add_score(user_id=user_id, amount=150)
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    assert user["rank"] == compute_rank(150)
    assert user["rank"] != "Unranked"


def test_compute_rank_thresholds():
    assert compute_rank(0) == "Unranked"
    assert compute_rank(99) == "Unranked"
    assert compute_rank(100) == "Rising"
    assert compute_rank(500) == "Contender"
    assert compute_rank(2000) == "Elite"
    assert compute_rank(5000) == "Legend"
    assert compute_rank(10_000) == "Legend"


# -- seasons ---------------------------------------------------------------


async def test_get_current_season_returns_matching_season(client):
    db = get_db()
    today = date.today()
    service = ProgressionService(db)
    await service._seasons.create(  # noqa: SLF001 — direct repo use is fine for test setup
        start_date=today - timedelta(days=10), end_date=today + timedelta(days=80)
    )
    await service._seasons.create(
        start_date=today - timedelta(days=200), end_date=today - timedelta(days=120)
    )

    season = await service.get_current_season(on=today)

    assert season is not None
    assert season.start_date <= today <= season.end_date


async def test_get_current_season_returns_none_when_no_season_active(client):
    service = ProgressionService(get_db())
    season = await service.get_current_season(on=date.today())
    assert season is None


# -- authorization: self-scoped endpoints -----------------------------------


async def test_get_my_progression_requires_auth(client):
    resp = await client.get("/v1/progression/me")
    assert resp.status_code == 401


async def test_get_my_progression_returns_caller_only(client):
    token_a, user_a = await _register(client, "prog_a@example.com")
    token_b, user_b = await _register(client, "prog_b@example.com")

    service = ProgressionService(get_db())
    await service.add_score(user_id=user_a, amount=1000)

    resp_a = await client.get("/v1/progression/me", headers=_auth(token_a))
    resp_b = await client.get("/v1/progression/me", headers=_auth(token_b))

    assert resp_a.json()["thesdel_score"] == 1000
    assert resp_b.json()["thesdel_score"] == 0  # user B's own data, unaffected by user A


async def test_list_my_badges_cannot_be_used_to_read_another_users_badges(client):
    token_a, user_a = await _register(client, "prog_c@example.com")
    token_b, user_b = await _register(client, "prog_d@example.com")

    db = get_db()
    badge_id = await _make_badge(db, name="Only A Has This")
    service = ProgressionService(db)
    await service.award_badge(user_id=user_a, badge_id=badge_id)

    resp_a = await client.get("/v1/progression/badges/me", headers=_auth(token_a))
    resp_b = await client.get("/v1/progression/badges/me", headers=_auth(token_b))

    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 0  # no user_id is ever taken from the client — self-scoped only


async def test_badge_catalog_endpoint_requires_auth(client):
    resp = await client.get("/v1/progression/badges")
    assert resp.status_code == 401


async def test_badge_catalog_endpoint_lists_seeded_badges(client):
    token, _ = await _register(client, "prog_e@example.com")
    db = get_db()
    await _make_badge(db, name="Catalog Badge 1")
    await _make_badge(db, name="Catalog Badge 2", criteria_type="other_type", criteria_value=1)

    resp = await client.get("/v1/progression/badges", headers=_auth(token))
    assert resp.status_code == 200
    names = {b["name"] for b in resp.json()}
    assert {"Catalog Badge 1", "Catalog Badge 2"} <= names
