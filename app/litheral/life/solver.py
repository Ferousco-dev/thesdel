"""Pro life-schedule layering: combines class blocks, study blocks (both
already conflict-free by construction — study never overlaps classes), and
routine inputs into a single layered schedule.

Per Backend Spec §5.1: conflicts are written with conflict_flag=true rather
than silently dropped, so the frontend can surface them (Frontend Spec
§6.3). A flexible routine that conflicts is retried in a free slot; a fixed
routine that conflicts is placed at its stated time anyway, flagged.

Pure functions, no I/O.
"""

from typing import NamedTuple

from app.shared.time_utils import minutes_to_time, time_to_minutes

STUDY_WINDOW_START_MINUTES = 6 * 60  # life layer allows earlier (e.g. gym) than study's 08:00
STUDY_WINDOW_END_MINUTES = 23 * 60


class FixedBlock(NamedTuple):
    source_type: str  # "class" | "study"
    source_id: str
    day_of_week: int
    start_minutes: int
    end_minutes: int


class RoutineInput(NamedTuple):
    routine_id: str
    days: list[int]
    start_minutes: int
    end_minutes: int
    is_flexible: bool


class LifeBlock(NamedTuple):
    source_type: str
    source_id: str
    day_of_week: int
    start_minutes: int
    end_minutes: int
    conflict_flag: bool


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _has_conflict(day_of_week: int, start: int, end: int, placed: list[LifeBlock]) -> bool:
    return any(
        b.day_of_week == day_of_week and _overlaps(start, end, b.start_minutes, b.end_minutes)
        for b in placed
    )


def _find_free_slot(
    day_of_week: int, duration: int, placed: list[LifeBlock]
) -> tuple[int, int] | None:
    day_blocks = sorted(
        (b for b in placed if b.day_of_week == day_of_week), key=lambda b: b.start_minutes
    )
    cursor = STUDY_WINDOW_START_MINUTES
    for b in day_blocks:
        if b.start_minutes - cursor >= duration:
            return cursor, cursor + duration
        cursor = max(cursor, b.end_minutes)
    if STUDY_WINDOW_END_MINUTES - cursor >= duration:
        return cursor, cursor + duration
    return None


def build_life_schedule(
    *, fixed_blocks: list[FixedBlock], routines: list[RoutineInput]
) -> list[LifeBlock]:
    # Classes and study blocks are placed first and are never flagged —
    # they're already mutually conflict-free by construction (the study
    # solver never overlaps class blocks). Routines layer on top of them.
    placed: list[LifeBlock] = [
        LifeBlock(
            source_type=b.source_type,
            source_id=b.source_id,
            day_of_week=b.day_of_week,
            start_minutes=b.start_minutes,
            end_minutes=b.end_minutes,
            conflict_flag=False,
        )
        for b in fixed_blocks
    ]

    for routine in routines:
        duration = routine.end_minutes - routine.start_minutes
        for day in routine.days:
            conflicts = _has_conflict(day, routine.start_minutes, routine.end_minutes, placed)

            if not conflicts:
                placed.append(
                    LifeBlock(
                        source_type="routine",
                        source_id=routine.routine_id,
                        day_of_week=day,
                        start_minutes=routine.start_minutes,
                        end_minutes=routine.end_minutes,
                        conflict_flag=False,
                    )
                )
                continue

            if routine.is_flexible:
                alternative = _find_free_slot(day, duration, placed)
                if alternative is not None:
                    start, end = alternative
                    placed.append(
                        LifeBlock(
                            source_type="routine",
                            source_id=routine.routine_id,
                            day_of_week=day,
                            start_minutes=start,
                            end_minutes=end,
                            conflict_flag=False,
                        )
                    )
                    continue

            # Fixed and conflicting, or flexible with no free slot found —
            # place at the stated time anyway, flagged. Never dropped.
            placed.append(
                LifeBlock(
                    source_type="routine",
                    source_id=routine.routine_id,
                    day_of_week=day,
                    start_minutes=routine.start_minutes,
                    end_minutes=routine.end_minutes,
                    conflict_flag=True,
                )
            )

    return placed


__all__ = [
    "FixedBlock",
    "RoutineInput",
    "LifeBlock",
    "build_life_schedule",
    "time_to_minutes",
    "minutes_to_time",
]
