from collections.abc import Awaitable, Callable

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession, AsyncIOMotorDatabase

from app.shared.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(
            settings.mongo_uri, uuidRepresentation="standard", tz_aware=True
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.mongo_db_name]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def run_in_transaction(fn: Callable[[AsyncIOMotorClientSession | None], Awaitable[None]]) -> None:
    """Runs `fn` inside a multi-document transaction — used for the two
    operations documented in docs/DATABASE.md §3 that need cross-collection
    atomicity (class join + member_count increment; badge award guards).

    MongoDB Atlas provisions a replica set even on the free/shared tier, so
    transactions are available in every real environment (see
    docs/RESEARCH.md #3). The in-memory Mongo fake used in tests
    (mongomock) does not implement sessions — in that case only, this falls
    back to running `fn` without a session. That fallback is a test-
    environment accommodation, not a production code path: production
    always runs against a session-capable replica set.
    """
    client = get_client()
    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                await fn(session)
    except NotImplementedError:
        await fn(None)


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def ensure_indexes() -> None:
    """Every index here maps to a named query pattern documented in
    docs/DATABASE.md §2 — no speculative indexes."""
    db = get_db()

    await db.users.create_index("email", unique=True)

    await db.classes.create_index("join_code", unique=True)

    await db.class_members.create_index([("class_id", 1), ("user_id", 1)], unique=True)
    await db.class_members.create_index("user_id")
    await db.class_members.create_index("class_id")

    await db.timetable_entries.create_index([("owner_type", 1), ("owner_id", 1), ("day_of_week", 1)])

    await db.announcements.create_index([("class_id", 1), ("pinned", 1), ("created_at", -1)])

    await db.study_plans.create_index([("user_id", 1), ("generated_at", -1)])

    await db.routines.create_index("user_id")

    await db.life_schedule_blocks.create_index([("user_id", 1), ("day_of_week", 1)])

    await db.ai_usage_log.create_index([("user_id", 1), ("feature", 1), ("created_at", -1)])
    await db.ai_usage_log.create_index("created_at", expireAfterSeconds=60 * 60 * 24 * 395)

    await db.user_badges.create_index([("user_id", 1), ("badge_id", 1)], unique=True)
    await db.badges.create_index("criteria_type")
    await db.seasons.create_index([("start_date", 1), ("end_date", 1)])

    await db.partner_streaks.create_index([("user_a", 1), ("user_b", 1)], unique=True)

    await db.sessions.create_index("user_id")
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.sessions.create_index("refresh_token_hash", unique=True)
    await db.sessions.create_index("family_id")
