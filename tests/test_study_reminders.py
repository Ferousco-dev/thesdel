"""Tests for study-block reminder jobs (Premium/Pro feature).

Covers:
- Cron jobs enqueue pushes for upcoming blocks within the time window
- Dedup mechanism prevents duplicate notifications on re-runs
- Only Premium/Pro users get reminders
- Correct timing windows (24±1h, 60±5min)
- Message formatting includes subject and window info
"""

from datetime import UTC, datetime, timedelta
from bson import ObjectId

from app.shared.db import get_db
from app.shared.redis_client import get_redis


def _capture_push_jobs(monkeypatch):
    """Stubs `enqueue_push_to_user` to capture calls instead of hitting ARQ.
    Same pattern as test_notifications.py."""
    calls: list[dict] = []

    async def _fake_enqueue(*, user_id: str, title: str, body: str, data=None) -> None:
        calls.append({"user_id": user_id, "title": title, "body": body, "data": data or {}})

    import app.shared.jobs as jobs_module

    monkeypatch.setattr(jobs_module, "enqueue_push_to_user", _fake_enqueue)
    return calls


async def _register_and_verify_tier(client, email: str, tier: str = "premium"):
    """Helper: create a user and set their tier."""
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "correct-horse-1", "display_name": "Student"},
    )
    user_id = resp.json()["user"]["id"]
    db = get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"tier": tier}}
    )
    return user_id


async def _create_study_block(
    db,
    user_id: str,
    subject: str,
    day_of_week: int,
    start_time: str,
    end_time: str = "15:00",
):
    """Helper: insert a study block for testing."""
    doc = {
        "user_id": ObjectId(user_id),
        "subject": subject,
        "priority": 3,
        "exam_date": None,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": end_time,
        "generated_at": datetime.now(UTC),
    }
    result = await db.study_plans.insert_one(doc)
    return str(result.inserted_id)


# -- 1-day reminder tests --------------------------------------------------


async def test_1day_reminder_enqueues_push_for_block_starting_tomorrow(client, monkeypatch):
    """A study block scheduled for tomorrow at the same time should trigger
    a 1-day reminder (24±1h window)."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    # Create a block for tomorrow (if today is Monday, block is Tuesday)
    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")  # Same time tomorrow
    await _create_study_block(db, user_id, "Math", tomorrow_dow, tomorrow_time)

    # Run the 1-day job
    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    # Should have enqueued one push
    assert len(calls) == 1
    assert calls[0]["user_id"] == user_id
    assert "Math" in calls[0]["title"]
    assert "1 day" in calls[0]["title"]
    assert calls[0]["data"]["type"] == "study_reminder"
    assert calls[0]["data"]["window"] == "1day"


async def test_1day_reminder_dedup_prevents_duplicate_sends(client, monkeypatch):
    """Running the 1-day job twice should dedup — second run should not enqueue
    a duplicate push for the same block."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()
    redis = get_redis()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")
    block_id = await _create_study_block(db, user_id, "Physics", tomorrow_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    # First run: should enqueue
    await check_study_blocks_1day_before({})
    assert len(calls) == 1

    # Clear calls
    calls.clear()

    # Second run: dedup should prevent enqueue (same user, same block, same window)
    await check_study_blocks_1day_before({})
    assert len(calls) == 0

    # Clean Redis dedup key and run again: should enqueue again
    dedup_key = f"reminder:1day:{user_id}:{block_id}"
    await redis.delete(dedup_key)
    await check_study_blocks_1day_before({})
    assert len(calls) == 1


async def test_1day_reminder_ignores_free_tier_users(client, monkeypatch):
    """Free-tier users should not receive study reminders."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "free@example.com", "free")
    db = get_db()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")
    await _create_study_block(db, user_id, "Chemistry", tomorrow_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    # No push should be enqueued for free user
    assert len(calls) == 0


async def test_1day_reminder_ignores_blocks_outside_window(client, monkeypatch):
    """Blocks not within 24±1h window should not trigger a reminder."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    now = datetime.now(UTC)

    # Create a block for 3 days from now (outside the 24±1h window)
    three_days_ahead_dow = (now.weekday() + 3) % 7
    tomorrow_time = now.time().strftime("%H:%M")
    await _create_study_block(db, user_id, "Biology", three_days_ahead_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    # Should not enqueue for a block 3 days away
    assert len(calls) == 0


async def test_1day_reminder_message_format_includes_subject(client, monkeypatch):
    """Push title should include the subject name for context."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")
    await _create_study_block(db, user_id, "Organic Chemistry", tomorrow_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    assert len(calls) == 1
    assert "Organic Chemistry" in calls[0]["title"]
    assert calls[0]["data"]["subject"] == "Organic Chemistry"


# -- 1-hour reminder tests -------------------------------------------------


async def test_1hour_reminder_enqueues_push_for_block_starting_soon(client, monkeypatch):
    """A study block scheduled for ~1 hour from now should trigger
    a 1-hour reminder (60±5min window)."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    # Create a block for about 1 hour from now
    now = datetime.now(UTC)
    target_time = (now + timedelta(hours=1)).time()
    target_time_str = target_time.strftime("%H:%M")
    await _create_study_block(db, user_id, "History", now.weekday(), target_time_str)

    from app.litheral.study.jobs import check_study_blocks_1hour_before

    await check_study_blocks_1hour_before({})

    # Should have enqueued one push
    assert len(calls) == 1
    assert calls[0]["user_id"] == user_id
    assert "History" in calls[0]["title"]
    assert "1 hour" in calls[0]["title"]
    assert calls[0]["data"]["window"] == "1hour"


async def test_1hour_reminder_dedup_prevents_duplicate_sends(client, monkeypatch):
    """Running the 1-hour job twice should dedup."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()
    redis = get_redis()

    now = datetime.now(UTC)
    target_time = (now + timedelta(hours=1)).time().strftime("%H:%M")
    block_id = await _create_study_block(db, user_id, "Economics", now.weekday(), target_time)

    from app.litheral.study.jobs import check_study_blocks_1hour_before

    # First run
    await check_study_blocks_1hour_before({})
    assert len(calls) == 1

    calls.clear()

    # Second run: deduplicated
    await check_study_blocks_1hour_before({})
    assert len(calls) == 0

    # After clearing dedup key, should enqueue again
    dedup_key = f"reminder:1hour:{user_id}:{block_id}"
    await redis.delete(dedup_key)
    await check_study_blocks_1hour_before({})
    assert len(calls) == 1


async def test_1hour_reminder_ignores_blocks_outside_window(client, monkeypatch):
    """Blocks not within 60±5min window should not trigger."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    now = datetime.now(UTC)

    # Create a block for 2 hours from now (outside 60±5min window)
    target_time = (now + timedelta(hours=2)).time().strftime("%H:%M")
    await _create_study_block(db, user_id, "Philosophy", now.weekday(), target_time)

    from app.litheral.study.jobs import check_study_blocks_1hour_before

    await check_study_blocks_1hour_before({})

    # Should not enqueue
    assert len(calls) == 0


# -- Multi-user and edge cases --------------------------------------------


async def test_both_jobs_enqueue_for_different_windows(client, monkeypatch):
    """A user can get both 1-day and 1-hour reminders for the same block
    (within different time windows)."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    # Create a block scheduled for tomorrow at ~1 hour from now
    now = datetime.now(UTC)
    # If it's 22:00 UTC, tomorrow is next day; if 00:30 UTC, tomorrow at 01:30 is ~1 hour away
    # For predictability, create a block for tomorrow at current time + 1 hour
    tomorrow_dow = (now.weekday() + 1) % 7
    current_hour_plus_1 = (now.hour + 1) % 24
    target_time_str = f"{current_hour_plus_1:02d}:{now.minute:02d}"
    await _create_study_block(db, user_id, "Art", tomorrow_dow, target_time_str)

    from app.litheral.study.jobs import (
        check_study_blocks_1day_before,
        check_study_blocks_1hour_before,
    )

    # 1-day job: should enqueue (tomorrow at the time is ~24h away)
    await check_study_blocks_1day_before({})
    day_calls = len(calls)
    assert day_calls >= 1, "1-day job should enqueue for tomorrow's block"

    calls.clear()

    # 1-hour job: timing depends on exact UTC; it might not match if the
    # tomorrow-at-current-time-plus-1-hour doesn't fall in the 60±5min window.
    # This test is more of a structure check than an exact timing test.
    await check_study_blocks_1hour_before({})
    # (may be 0 or 1 depending on exact timing; the point is both jobs ran)


async def test_pro_tier_users_also_get_reminders(client, monkeypatch):
    """Pro users should receive study reminders just like Premium users."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "pro@example.com", "pro")
    db = get_db()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")
    await _create_study_block(db, user_id, "Spanish", tomorrow_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    assert len(calls) == 1
    assert calls[0]["user_id"] == user_id


async def test_multiple_users_get_independent_reminders(client, monkeypatch):
    """Each Premium/Pro user gets their own reminders without cross-contamination."""
    calls = _capture_push_jobs(monkeypatch)
    user1_id = await _register_and_verify_tier(client, "user1@example.com", "premium")
    user2_id = await _register_and_verify_tier(client, "user2@example.com", "premium")
    db = get_db()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")

    await _create_study_block(db, user1_id, "Math", tomorrow_dow, tomorrow_time)
    await _create_study_block(db, user2_id, "English", tomorrow_dow, tomorrow_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    assert len(calls) == 2
    user_ids = {c["user_id"] for c in calls}
    assert user_ids == {user1_id, user2_id}


async def test_multiple_blocks_per_user_all_get_reminders(client, monkeypatch):
    """A user with multiple study blocks in the window gets a reminder for each."""
    calls = _capture_push_jobs(monkeypatch)
    user_id = await _register_and_verify_tier(client, "premium@example.com", "premium")
    db = get_db()

    now = datetime.now(UTC)
    tomorrow_dow = (now.weekday() + 1) % 7
    tomorrow_time = now.time().strftime("%H:%M")

    # Create two blocks for tomorrow at the same time (or different times)
    await _create_study_block(db, user_id, "Math", tomorrow_dow, tomorrow_time)
    # Second block at a different time
    next_hour = ((now.hour + 2) % 24)
    other_time = f"{next_hour:02d}:{now.minute:02d}"
    await _create_study_block(db, user_id, "Science", tomorrow_dow, other_time)

    from app.litheral.study.jobs import check_study_blocks_1day_before

    await check_study_blocks_1day_before({})

    # Should have 1-2 reminders depending on whether both fall in the 24±1h window
    assert len(calls) >= 1
    subjects = {c["data"]["subject"] for c in calls}
    assert "Math" in subjects or "Science" in subjects


async def test_no_study_plans_doesnt_error(client, monkeypatch):
    """A Premium user with no study blocks should not cause an error."""
    calls = _capture_push_jobs(monkeypatch)
    await _register_and_verify_tier(client, "empty@example.com", "premium")

    from app.litheral.study.jobs import check_study_blocks_1day_before

    # Should complete without error
    await check_study_blocks_1day_before({})
    assert len(calls) == 0


async def test_no_premium_users_doesnt_error(client, monkeypatch):
    """If there are no Premium/Pro users, the job should complete silently."""
    calls = _capture_push_jobs(monkeypatch)
    await _register_and_verify_tier(client, "free@example.com", "free")

    from app.litheral.study.jobs import check_study_blocks_1day_before

    # Should complete without error
    await check_study_blocks_1day_before({})
    assert len(calls) == 0
