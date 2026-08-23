from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.litheral.life import solver
from app.litheral.life.repository import LifeScheduleRepository
from app.litheral.life.schemas import LifeBlockPublic
from app.litheral.study.service import LitheralStudyService
from app.notifications.service import NotificationService
from app.routines.service import RoutineService
from app.timetable.service import TimetableService
from app.usage.service import UNLIMITED, AiUsageService

FEATURE_GENERATE = "life_generate"
FEATURE_ADJUST = "life_adjust"


class LitheralLifeService:
    """Pro scope: reads timetable_entries, study_plans (via
    LitheralStudyService's public interface, not its repository), and
    routines, outputs life_schedule_blocks. This is the ONLY litheral
    module allowed to touch routines — see docs/DATABASE.md §1 and
    RULES.md forbidden patterns."""

    def __init__(self, db: AsyncIOMotorDatabase, redis: Redis, *, adjust_cap: int) -> None:
        self._repo = LifeScheduleRepository(db)
        self._timetable = TimetableService(db)
        self._study = LitheralStudyService(db, redis, regenerate_cap=0)
        self._routines = RoutineService(db)
        self._usage = AiUsageService(db, redis)
        self._notifications = NotificationService(db, redis)
        self._adjust_cap = adjust_cap

    async def generate(self, *, user_id: str) -> list[LifeBlockPublic]:
        return await self._run(user_id=user_id, feature=FEATURE_GENERATE, limit=UNLIMITED)

    async def adjust(self, *, user_id: str) -> list[LifeBlockPublic]:
        return await self._run(user_id=user_id, feature=FEATURE_ADJUST, limit=self._adjust_cap)

    async def list_blocks(self, *, user_id: str) -> list[LifeBlockPublic]:
        docs = await self._repo.list_for_user(user_id)
        return [_to_public(doc) for doc in docs]

    async def _run(self, *, user_id: str, feature: str, limit: int) -> list[LifeBlockPublic]:
        log_id = await self._usage.check_and_reserve(user_id=user_id, feature=feature, limit=limit)

        try:
            timetable_entries = await self._timetable.list_personal(user_id=user_id)
            study_blocks = await self._study.list_blocks(user_id=user_id)
            routines = await self._routines.list_for_user(user_id=user_id)

            fixed = [
                solver.FixedBlock(
                    source_type="class",
                    source_id=e.id,
                    day_of_week=e.day_of_week,
                    start_minutes=solver.time_to_minutes(e.start_time),
                    end_minutes=solver.time_to_minutes(e.end_time),
                )
                for e in timetable_entries
            ] + [
                solver.FixedBlock(
                    source_type="study",
                    source_id=s.id,
                    day_of_week=s.day_of_week,
                    start_minutes=solver.time_to_minutes(s.start_time),
                    end_minutes=solver.time_to_minutes(s.end_time),
                )
                for s in study_blocks
            ]

            routine_inputs = [
                solver.RoutineInput(
                    routine_id=r.id,
                    days=r.days,
                    start_minutes=solver.time_to_minutes(r.start_time),
                    end_minutes=solver.time_to_minutes(r.end_time),
                    is_flexible=r.is_flexible,
                )
                for r in routines
            ]

            life_blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=routine_inputs)

            docs = await self._repo.replace_all_for_user(
                user_id=user_id,
                blocks=[
                    {
                        "source_type": b.source_type,
                        "source_id": b.source_id,
                        "day_of_week": b.day_of_week,
                        "start_time": solver.minutes_to_time(b.start_minutes),
                        "end_time": solver.minutes_to_time(b.end_minutes),
                        "conflict_flag": b.conflict_flag,
                    }
                    for b in life_blocks
                ],
            )
        except Exception:
            await self._usage.mark_failed(log_id)
            raise

        await self._usage.mark_succeeded(log_id)

        # Pro life-schedule conflict alert (docs/ARCHITECTURE.md §11) —
        # exactly one push for this run if ANY block conflicts, never one
        # per conflicting block.
        if any(doc["conflict_flag"] for doc in docs):
            await self._notifications.notify_life_schedule_conflict(user_id=user_id)

        return [_to_public(doc) for doc in docs]


def _to_public(doc: dict) -> LifeBlockPublic:
    return LifeBlockPublic(
        id=str(doc["_id"]),
        source_type=doc["source_type"],
        source_id=doc["source_id"],
        day_of_week=doc["day_of_week"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        conflict_flag=doc["conflict_flag"],
        generated_at=doc["generated_at"],
    )
