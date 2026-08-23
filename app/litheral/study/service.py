from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.litheral.study import solver
from app.litheral.study.repository import StudyPlanRepository
from app.litheral.study.schemas import (
    GenerateStudyPlanRequest,
    RegenerateBlockResponse,
    StudyBlockPublic,
)
from app.shared.errors import ConflictError, NotFoundError
from app.timetable.service import TimetableService
from app.usage.service import UNLIMITED, AiUsageService

FEATURE_GENERATE = "study_generate"
FEATURE_REGENERATE = "study_regenerate"


class LitheralStudyService:
    """Premium scope boundary: reads timetable_entries (via
    TimetableService's public interface) and study_plans only. Never
    imports anything from app.routines — see RULES.md forbidden patterns
    and docs/DATABASE.md §1."""

    def __init__(self, db: AsyncIOMotorDatabase, redis: Redis, *, regenerate_cap: int) -> None:
        self._db = db
        self._repo = StudyPlanRepository(db)
        self._timetable = TimetableService(db)
        self._usage = AiUsageService(db, redis)
        self._regenerate_cap = regenerate_cap

    async def generate(
        self, *, user_id: str, body: GenerateStudyPlanRequest
    ) -> list[StudyBlockPublic]:
        log_id = await self._usage.check_and_reserve(
            user_id=user_id, feature=FEATURE_GENERATE, limit=UNLIMITED
        )

        try:
            timetable_entries = await self._timetable.list_personal(user_id=user_id)
            busy = [
                solver.BusyInterval(
                    day_of_week=e.day_of_week,
                    start_minutes=solver.time_to_minutes(e.start_time),
                    end_minutes=solver.time_to_minutes(e.end_time),
                )
                for e in timetable_entries
            ]

            subjects = _resolve_subjects(body, timetable_entries)

            blocks = solver.generate_study_blocks(
                busy=busy, subjects=subjects, today=datetime.now(UTC).date()
            )

            docs = await self._repo.replace_all_for_user(
                user_id=user_id,
                blocks=[
                    {
                        "subject": b.subject,
                        "priority": b.priority,
                        "exam_date": b.exam_date.isoformat() if b.exam_date else None,
                        "day_of_week": b.day_of_week,
                        "start_time": solver.minutes_to_time(b.start_minutes),
                        "end_time": solver.minutes_to_time(b.end_minutes),
                    }
                    for b in blocks
                ],
            )
        except Exception:
            await self._usage.mark_failed(log_id)
            raise

        await self._usage.mark_succeeded(log_id)
        return [_to_public(doc) for doc in docs]

    async def list_blocks(self, *, user_id: str) -> list[StudyBlockPublic]:
        docs = await self._repo.list_for_user(user_id)
        return [_to_public(doc) for doc in docs]

    async def regenerate_block(self, *, user_id: str, block_id: str) -> RegenerateBlockResponse:
        existing = await self._repo.find_by_id(block_id)
        if existing is None or str(existing["user_id"]) != user_id:
            raise NotFoundError()

        log_id = await self._usage.check_and_reserve(
            user_id=user_id, feature=FEATURE_REGENERATE, limit=self._regenerate_cap
        )

        try:
            timetable_entries = await self._timetable.list_personal(user_id=user_id)
            busy = [
                solver.BusyInterval(
                    day_of_week=e.day_of_week,
                    start_minutes=solver.time_to_minutes(e.start_time),
                    end_minutes=solver.time_to_minutes(e.end_time),
                )
                for e in timetable_entries
            ]

            other_blocks = await self._repo.list_for_user(user_id)
            other_busy = [
                solver.BusyInterval(
                    day_of_week=b["day_of_week"],
                    start_minutes=solver.time_to_minutes(b["start_time"]),
                    end_minutes=solver.time_to_minutes(b["end_time"]),
                )
                for b in other_blocks
                if b["_id"] != existing["_id"]
            ]

            replacement = solver.find_replacement_slot(
                busy=busy,
                other_study_blocks=other_busy,
                day_of_week=existing["day_of_week"],
                exclude_start_minutes=solver.time_to_minutes(existing["start_time"]),
                today=datetime.now(UTC).date(),
            )
        except Exception:
            await self._usage.mark_failed(log_id)
            raise

        if replacement is None:
            await self._usage.mark_failed(log_id)
            raise ConflictError(
                "No alternative time slot is available for this block right now."
            )

        day_of_week, start_minutes, end_minutes = replacement
        updated = await self._repo.replace_block(
            existing["_id"],
            {
                "day_of_week": day_of_week,
                "start_time": solver.minutes_to_time(start_minutes),
                "end_time": solver.minutes_to_time(end_minutes),
            },
        )
        await self._usage.mark_succeeded(log_id)

        status = await self._usage.get_status(
            user_id=user_id, feature=FEATURE_REGENERATE, limit=self._regenerate_cap
        )
        return RegenerateBlockResponse(
            block=_to_public(updated),
            remaining_regenerations=max(0, status.limit - status.used),
        )


def _resolve_subjects(
    body: GenerateStudyPlanRequest, timetable_entries: list
) -> list[solver.SubjectInput]:
    if body.subjects:
        return [
            solver.SubjectInput(subject=s.subject, priority=s.priority, exam_date=s.exam_date)
            for s in body.subjects
        ]

    # Pulled from timetable per Frontend Spec §5.1, deduplicated, in
    # first-seen order for determinism.
    seen: dict[str, None] = {}
    for entry in timetable_entries:
        seen.setdefault(entry.subject, None)
    return [solver.SubjectInput(subject=subject, priority=None, exam_date=None) for subject in seen]


def _to_public(doc: dict) -> StudyBlockPublic:
    exam_date = doc.get("exam_date")
    return StudyBlockPublic(
        id=str(doc["_id"]),
        subject=doc["subject"],
        priority=doc.get("priority"),
        exam_date=datetime.fromisoformat(exam_date).date() if exam_date else None,
        day_of_week=doc["day_of_week"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        generated_at=doc["generated_at"],
    )
