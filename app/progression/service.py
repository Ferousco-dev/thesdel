"""Business logic for badges, thesdel_score, seasons, and rank.

Only this module's service mutates `users.thesdel_score` / `users.rank`,
analogous to the billing-only `users.tier` mutation rule (RULES.md forbidden
patterns). Other modules call `ProgressionService.award_badge` /
`evaluate_and_award` / `add_score` as public service-interface calls — they
never touch `app/progression/repository.py` directly (module import
boundary, docs/ARCHITECTURE.md §2).
"""

from datetime import UTC, date, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.progression.repository import (
    BadgeRepository,
    ProgressionUserRepository,
    SeasonRepository,
    UserBadgeRepository,
)
from app.progression.schemas import (
    BadgePublic,
    ProgressionMe,
    SeasonPublic,
    UserBadgePublic,
)
from app.shared.errors import NotFoundError

# Rank heuristic — first-pass, absolute-score threshold tiers. Not spec'd
# anywhere in the Backend Spec docs available to this module; logged as a
# deliberate open-ended call in docs/DECISIONS.md ADR-008. Season-relative
# ranking (e.g. leaderboard percentile within the current season) is a
# documented follow-up, not built here.
_RANK_THRESHOLDS: list[tuple[int, str]] = [
    (0, "Unranked"),
    (100, "Rising"),
    (500, "Contender"),
    (2000, "Elite"),
    (5000, "Legend"),
]


def compute_rank(score: int) -> str:
    """Pure function: score -> rank tier. See ADR-008 for the heuristic's
    rationale and its documented follow-up (season-relative ranking)."""
    rank = _RANK_THRESHOLDS[0][1]
    for threshold, tier in _RANK_THRESHOLDS:
        if score >= threshold:
            rank = tier
    return rank


class ProgressionService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._badges = BadgeRepository(db)
        self._user_badges = UserBadgeRepository(db)
        self._users = ProgressionUserRepository(db)
        self._seasons = SeasonRepository(db)

    # -- badges ---------------------------------------------------------

    async def list_badge_catalog(self) -> list[BadgePublic]:
        docs = await self._badges.list_all()
        return [_badge_to_public(doc) for doc in docs]

    async def list_badges_for_user(self, *, user_id: str) -> list[UserBadgePublic]:
        user_oid = ObjectId(user_id)
        earned = await self._user_badges.list_for_user(user_oid)
        if not earned:
            return []
        badge_ids = {doc["badge_id"] for doc in earned}
        badges_by_id: dict[ObjectId, dict[str, Any]] = {}
        for badge_id in badge_ids:
            badge = await self._badges.find_by_id(badge_id)
            if badge is not None:
                badges_by_id[badge_id] = badge

        result: list[UserBadgePublic] = []
        for doc in earned:
            badge = badges_by_id.get(doc["badge_id"])
            if badge is None:
                continue  # badge catalog entry removed since earning — skip, don't error
            result.append(
                UserBadgePublic(
                    badge_id=str(badge["_id"]),
                    family=badge["family"],
                    name=badge["name"],
                    earned_at=doc["earned_at"],
                )
            )
        return result

    async def award_badge(self, *, user_id: str, badge_id: str) -> bool:
        """Internal, service-to-service call — never exposed as a public
        "award me a badge" endpoint. The caller (e.g. routines/study
        completing a session) is responsible for having already evaluated
        that the user's action satisfies the badge's criteria server-side.
        Idempotent: returns False (not an error) if already awarded.
        """
        badge_oid = ObjectId(badge_id)
        badge = await self._badges.find_by_id(badge_oid)
        if badge is None:
            raise NotFoundError("Badge does not exist.")
        user_oid = ObjectId(user_id)
        # Pre-check + insert (mirrors classes.join_class's pattern): the
        # pre-check makes idempotency work even without the unique index
        # present (e.g. before ensure_indexes() has run); the insert's
        # DuplicateKeyError catch in the repository is the race-condition
        # backstop for concurrent at-least-once triggering, per RULES.md
        # #10-12 and docs/DATABASE.md §3 "Badge award".
        if await self._user_badges.has_badge(user_id=user_oid, badge_id=badge_oid):
            return False
        return await self._user_badges.award(user_id=user_oid, badge_id=badge_oid)

    async def evaluate_and_award(
        self, *, user_id: str, criteria_type: str, current_value: Any
    ) -> list[str]:
        """Data-driven award mechanism: given an event (criteria_type,
        current_value — e.g. "study_sessions_completed", 5), finds every
        badge of that criteria_type whose criteria_value is met and awards
        any not already earned. Returns the ids of newly-awarded badges.

        This is the generic mechanism the ~225-badge catalog is meant to
        drive — badges are data, not hardcoded per-family logic. See
        migrations/0001_seed_progression_badges.py for the (illustrative,
        non-exhaustive) seed set.
        """
        candidates = await self._badges.list_by_criteria_type(criteria_type)
        newly_awarded: list[str] = []
        user_oid = ObjectId(user_id)
        for badge in candidates:
            if not _criteria_met(badge["criteria_value"], current_value):
                continue
            if await self._user_badges.has_badge(user_id=user_oid, badge_id=badge["_id"]):
                continue
            awarded = await self._user_badges.award(user_id=user_oid, badge_id=badge["_id"])
            if awarded:
                newly_awarded.append(str(badge["_id"]))
        return newly_awarded

    # -- thesdel_score / rank --------------------------------------------

    async def add_score(self, *, user_id: str, amount: int) -> int:
        """Atomic, permanent, always-increasing per docs/DATABASE.md §1.
        Never allow a negative/zero delta through this path — that's the
        entire guarantee this module exists to protect."""
        if amount <= 0:
            raise ValueError("thesdel_score can only increase; amount must be positive.")
        new_score = await self._users.increment_score(ObjectId(user_id), amount)
        if new_score is None:
            raise NotFoundError("User not found.")
        await self.refresh_rank(user_id=user_id, score=new_score)
        return new_score

    async def refresh_rank(self, *, user_id: str, score: int | None = None) -> str:
        user_oid = ObjectId(user_id)
        if score is None:
            user_doc = await self._users.find_by_id(user_oid)
            if user_doc is None:
                raise NotFoundError("User not found.")
            score = user_doc["thesdel_score"]
        rank = compute_rank(score)
        await self._users.set_rank(user_oid, rank)
        return rank

    # -- seasons ----------------------------------------------------------

    async def get_current_season(self, *, on: date | None = None) -> SeasonPublic | None:
        doc = await self._seasons.find_current(on=on or datetime.now(UTC).date())
        if doc is None:
            return None
        return SeasonPublic(
            id=str(doc["_id"]),
            start_date=doc["start_date"].date(),
            end_date=doc["end_date"].date(),
        )

    # -- composite read for the "me" endpoint ------------------------------

    async def get_summary(self, *, user_id: str) -> ProgressionMe:
        user_doc = await self._users.find_by_id(ObjectId(user_id))
        if user_doc is None:
            raise NotFoundError("User not found.")
        season = await self.get_current_season()
        return ProgressionMe(
            thesdel_score=user_doc["thesdel_score"],
            rank=user_doc["rank"],
            current_season=season,
        )


def _criteria_met(criteria_value: Any, current_value: Any) -> bool:
    """Badges are awarded once `current_value` reaches `criteria_value`.
    Both are expected to be directly comparable (int thresholds, or an
    exact-match string/bool for milestone-style criteria)."""
    try:
        return bool(current_value >= criteria_value)
    except TypeError:
        return bool(current_value == criteria_value)


def _badge_to_public(doc: dict[str, Any]) -> BadgePublic:
    return BadgePublic(
        id=str(doc["_id"]),
        family=doc["family"],
        name=doc["name"],
        criteria_type=doc["criteria_type"],
        criteria_value=doc["criteria_value"],
    )
