from datetime import date

from app.litheral.study import solver


def test_free_intervals_excludes_busy_blocks():
    busy = [solver.BusyInterval(day_of_week=1, start_minutes=9 * 60, end_minutes=11 * 60)]
    free = solver.free_intervals_for_day(1, busy, today=date(2026, 1, 1))

    assert free == [
        solver.FreeInterval(1, solver.STUDY_WINDOW_START_MINUTES, 9 * 60),
        solver.FreeInterval(1, 11 * 60, solver.STUDY_WINDOW_END_MINUTES),
    ]


def test_free_intervals_full_day_when_no_classes():
    free = solver.free_intervals_for_day(3, [], today=date(2026, 1, 1))
    assert free == [
        solver.FreeInterval(3, solver.STUDY_WINDOW_START_MINUTES, solver.STUDY_WINDOW_END_MINUTES)
    ]


def test_generate_study_blocks_never_overlaps_class_blocks():
    busy = [
        solver.BusyInterval(day_of_week=0, start_minutes=9 * 60, end_minutes=17 * 60),
    ]
    subjects = [solver.SubjectInput(subject="Math", priority=None, exam_date=None)]
    blocks = solver.generate_study_blocks(busy=busy, subjects=subjects, today=date(2026, 1, 1))

    day_zero_blocks = [b for b in blocks if b.day_of_week == 0]
    for b in day_zero_blocks:
        assert b.end_minutes <= 9 * 60 or b.start_minutes >= 17 * 60


def test_generate_study_blocks_respects_daily_minute_cap():
    subjects = [solver.SubjectInput(subject="Physics", priority=None, exam_date=None)]
    blocks = solver.generate_study_blocks(busy=[], subjects=subjects, today=date(2026, 1, 1))

    per_day: dict[int, int] = {}
    for b in blocks:
        per_day[b.day_of_week] = per_day.get(b.day_of_week, 0) + (b.end_minutes - b.start_minutes)

    for minutes in per_day.values():
        assert minutes <= solver.MAX_STUDY_MINUTES_PER_DAY


def test_generate_study_blocks_empty_subjects_returns_nothing():
    assert solver.generate_study_blocks(busy=[], subjects=[], today=date(2026, 1, 1)) == []


def test_higher_priority_subject_gets_earlier_slots():
    subjects = [
        solver.SubjectInput(subject="Low", priority=1, exam_date=None),
        solver.SubjectInput(subject="High", priority=5, exam_date=None),
    ]
    blocks = solver.generate_study_blocks(busy=[], subjects=subjects, today=date(2026, 1, 1))

    first_block = min(blocks, key=lambda b: (b.day_of_week, b.start_minutes))
    assert first_block.subject == "High"


def test_find_replacement_slot_avoids_other_study_blocks():
    busy: list[solver.BusyInterval] = []
    other_blocks = [solver.BusyInterval(day_of_week=2, start_minutes=8 * 60, end_minutes=9 * 60)]

    replacement = solver.find_replacement_slot(
        busy=busy,
        other_study_blocks=other_blocks,
        day_of_week=2,
        exclude_start_minutes=8 * 60,
        today=date(2026, 1, 1),
    )

    assert replacement is not None
    day, start, end = replacement
    assert day == 2
    assert not (start < 9 * 60 and end > 8 * 60)  # doesn't overlap the other block
