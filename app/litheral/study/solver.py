"""Rules-based constraint solver for Litheral study-plan generation.

Per Backend Spec §5.2: V1 avoids an adaptive ML model — this is a
constraint/bin-packing algorithm (free time slots around fixed class
blocks, weighted by priority/exam proximity), not an LLM call. An LLM is
reserved for natural-language timetable-import parsing only (see
docs/DECISIONS.md ADR-003), never for this slotting math.

Pure functions, no I/O — easy to unit test in isolation from the DB.
"""

from datetime import date
from typing import NamedTuple

STUDY_WINDOW_START_MINUTES = 8 * 60  # 08:00
STUDY_WINDOW_END_MINUTES = 22 * 60  # 22:00
MIN_BLOCK_MINUTES = 30
MAX_BLOCK_MINUTES = 60
MAX_STUDY_MINUTES_PER_DAY = 120
EXAM_URGENCY_WINDOW_DAYS = 14


class BusyInterval(NamedTuple):
    day_of_week: int
    start_minutes: int
    end_minutes: int


class FreeInterval(NamedTuple):
    day_of_week: int
    start_minutes: int
    end_minutes: int

    @property
    def duration(self) -> int:
        return self.end_minutes - self.start_minutes


class SubjectInput(NamedTuple):
    subject: str
    priority: int | None
    exam_date: date | None


class StudyBlock(NamedTuple):
    subject: str
    priority: int | None
    exam_date: date | None
    day_of_week: int
    start_minutes: int
    end_minutes: int


def time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_time(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def free_intervals_for_day(
    day_of_week: int, busy: list[BusyInterval], *, today: date
) -> list[FreeInterval]:
    day_busy = sorted(
        (b for b in busy if b.day_of_week == day_of_week), key=lambda b: b.start_minutes
    )
    free: list[FreeInterval] = []
    cursor = STUDY_WINDOW_START_MINUTES
    for b in day_busy:
        if b.start_minutes > cursor:
            free.append(FreeInterval(day_of_week, cursor, min(b.start_minutes, STUDY_WINDOW_END_MINUTES)))
        cursor = max(cursor, b.end_minutes)
    if cursor < STUDY_WINDOW_END_MINUTES:
        free.append(FreeInterval(day_of_week, cursor, STUDY_WINDOW_END_MINUTES))
    return [f for f in free if f.duration >= MIN_BLOCK_MINUTES]


def _subject_score(subject: SubjectInput, *, today: date) -> float:
    score = float(subject.priority or 0)
    if subject.exam_date is not None:
        days_until = (subject.exam_date - today).days
        if 0 <= days_until <= EXAM_URGENCY_WINDOW_DAYS:
            score += (EXAM_URGENCY_WINDOW_DAYS - days_until) * 2
    return score


def _split_into_blocks(interval: FreeInterval) -> list[tuple[int, int]]:
    chunks = []
    cursor = interval.start_minutes
    while interval.end_minutes - cursor >= MIN_BLOCK_MINUTES:
        block_end = min(cursor + MAX_BLOCK_MINUTES, interval.end_minutes)
        chunks.append((cursor, block_end))
        cursor = block_end
    return chunks


def generate_study_blocks(
    *, busy: list[BusyInterval], subjects: list[SubjectInput], today: date
) -> list[StudyBlock]:
    """Round-robins available free-time chunks across subjects, highest
    score first, capped at MAX_STUDY_MINUTES_PER_DAY per day. Deterministic
    given the same inputs — no randomness, so results are reproducible and
    testable."""
    if not subjects:
        return []

    ranked_subjects = sorted(subjects, key=lambda s: _subject_score(s, today=today), reverse=True)

    blocks: list[StudyBlock] = []
    minutes_used_per_day: dict[int, int] = {d: 0 for d in range(7)}
    subject_cycle_index = 0

    for day_of_week in range(7):
        free = free_intervals_for_day(day_of_week, busy, today=today)
        chunks = [chunk for interval in free for chunk in _split_into_blocks(interval)]

        for chunk_start, chunk_end in chunks:
            if minutes_used_per_day[day_of_week] >= MAX_STUDY_MINUTES_PER_DAY:
                break
            remaining_budget = MAX_STUDY_MINUTES_PER_DAY - minutes_used_per_day[day_of_week]
            block_end = min(chunk_end, chunk_start + remaining_budget)
            if block_end - chunk_start < MIN_BLOCK_MINUTES:
                continue

            subject = ranked_subjects[subject_cycle_index % len(ranked_subjects)]
            subject_cycle_index += 1

            blocks.append(
                StudyBlock(
                    subject=subject.subject,
                    priority=subject.priority,
                    exam_date=subject.exam_date,
                    day_of_week=day_of_week,
                    start_minutes=chunk_start,
                    end_minutes=block_end,
                )
            )
            minutes_used_per_day[day_of_week] += block_end - chunk_start

    return blocks


def find_replacement_slot(
    *,
    busy: list[BusyInterval],
    other_study_blocks: list[BusyInterval],
    day_of_week: int,
    exclude_start_minutes: int,
    today: date,
) -> tuple[int, int, int] | None:
    """Used by single-block regenerate: finds a different free slot for the
    same subject, on the same day, avoiding both class blocks and the
    user's other current study blocks. Returns (day, start, end) or None if
    no alternative slot exists — caller surfaces a clear failure rather
    than silently keeping the stale block."""
    combined_busy = [*busy, *other_study_blocks]
    free = free_intervals_for_day(day_of_week, combined_busy, today=today)
    chunks = [chunk for interval in free for chunk in _split_into_blocks(interval)]
    candidates = [c for c in chunks if c[0] != exclude_start_minutes]
    if not candidates:
        candidates = chunks
    if not candidates:
        return None
    start, end = candidates[0]
    return day_of_week, start, min(end, start + MAX_BLOCK_MINUTES)
