from app.litheral.life import solver


def test_non_conflicting_routine_is_placed_as_is():
    fixed = [solver.FixedBlock("class", "c1", 0, 9 * 60, 10 * 60)]
    routines = [solver.RoutineInput("r1", days=[0], start_minutes=18 * 60, end_minutes=19 * 60, is_flexible=False)]

    blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=routines)
    routine_block = next(b for b in blocks if b.source_type == "routine")
    assert routine_block.conflict_flag is False
    assert routine_block.start_minutes == 18 * 60


def test_fixed_routine_conflict_is_flagged_not_dropped():
    fixed = [solver.FixedBlock("class", "c1", 0, 9 * 60, 11 * 60)]
    routines = [solver.RoutineInput("r1", days=[0], start_minutes=9 * 60, end_minutes=10 * 60, is_flexible=False)]

    blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=routines)
    routine_blocks = [b for b in blocks if b.source_type == "routine"]
    assert len(routine_blocks) == 1  # never silently dropped
    assert routine_blocks[0].conflict_flag is True
    assert routine_blocks[0].start_minutes == 9 * 60  # kept at stated time


def test_flexible_routine_conflict_moves_to_free_slot():
    # Busy from window-start through 17:00, so the only free slot is after
    # the class block — this isolates "moved later" from "found an earlier
    # gap", unlike a class block that starts mid-window.
    fixed = [solver.FixedBlock("class", "c1", 0, solver.STUDY_WINDOW_START_MINUTES, 17 * 60)]
    routines = [solver.RoutineInput("r1", days=[0], start_minutes=9 * 60, end_minutes=10 * 60, is_flexible=True)]

    blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=routines)
    routine_block = next(b for b in blocks if b.source_type == "routine")
    assert routine_block.conflict_flag is False
    assert routine_block.start_minutes >= 17 * 60  # moved after the class block


def test_flexible_routine_with_no_free_slot_falls_back_flagged():
    # Busy the entire day so no free slot exists anywhere.
    fixed = [solver.FixedBlock("class", "c1", 0, solver.STUDY_WINDOW_START_MINUTES, solver.STUDY_WINDOW_END_MINUTES)]
    routines = [solver.RoutineInput("r1", days=[0], start_minutes=9 * 60, end_minutes=10 * 60, is_flexible=True)]

    blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=routines)
    routine_blocks = [b for b in blocks if b.source_type == "routine"]
    assert len(routine_blocks) == 1
    assert routine_blocks[0].conflict_flag is True


def test_classes_and_study_blocks_are_never_flagged():
    fixed = [
        solver.FixedBlock("class", "c1", 0, 9 * 60, 10 * 60),
        solver.FixedBlock("study", "s1", 0, 10 * 60, 11 * 60),
    ]
    blocks = solver.build_life_schedule(fixed_blocks=fixed, routines=[])
    assert all(b.conflict_flag is False for b in blocks)
    assert len(blocks) == 2
