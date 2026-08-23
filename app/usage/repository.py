from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class AiUsageRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def log_attempt(self, *, user_id: str, feature: str) -> ObjectId:
        # Logged on attempt, not just completion, so retries are still
        # capped — see Backend Spec §5.3 step 5 and docs/ARCHITECTURE.md §13.
        doc = {
            "user_id": ObjectId(user_id),
            "feature": feature,
            "tokens_used": None,
            "cost_estimate": None,
            "status": "attempted",
            "created_at": datetime.now(UTC),
        }
        result = await self._db.ai_usage_log.insert_one(doc)
        return result.inserted_id

    async def mark_outcome(
        self, log_id: ObjectId, *, status: str, tokens_used: int | None = None
    ) -> None:
        await self._db.ai_usage_log.update_one(
            {"_id": log_id}, {"$set": {"status": status, "tokens_used": tokens_used}}
        )

    async def count_for_period(self, *, user_id: str, feature: str, period_start: datetime) -> int:
        """Durable backstop count — the live enforcement point is the Redis
        counter (docs/DECISIONS.md ADR-004); this is used for the
        GET /v1/usage/ai display endpoint, not for enforcement itself."""
        return await self._db.ai_usage_log.count_documents(
            {
                "user_id": ObjectId(user_id),
                "feature": feature,
                "created_at": {"$gte": period_start},
            }
        )
