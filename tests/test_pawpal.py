import datetime as dt

import pytest

from pawpal_system import (
    App,
    Task,
    Pet,
    Scheduler,
    TaskInstance,
    TaskType,
    Priority,
    TaskStatus,
)


def make_task(name="Walk", start_hour=8):
    return Task(
        name,
        None,
        dt.datetime(2026, 7, 4, start_hour, 0),
        dt.timedelta(minutes=30),
        dt.timedelta(days=1),
        TaskType.WALK,
        Priority.MED,
        dt.timedelta(hours=1),
    )


def test_add_task():
    # Verify that adding a task to a Pet increases that pet's task count.
    pet = Pet("Hans", "dog", "husky", dt.datetime(2023, 6, 2))
    assert len(pet.tasks) == 0

    pet.addTask(make_task())
    assert len(pet.tasks) == 1

    pet.addTask(make_task("Feed", start_hour=9))
    assert len(pet.tasks) == 2


def test_mark_complete():
    # Verify that calling mark_complete() actually changes the task's status.
    app = App()
    pet_id = app.owner.addPet(Pet("Hans", "dog", "husky", dt.datetime(2023, 6, 2)))
    app.addTask(pet_id, make_task())

    ti = app.scheduler.schedule[0]
    assert ti.status == TaskStatus.PENDING

    app.scheduler.mark_complete(ti, TaskStatus.DONE)
    assert ti.status != TaskStatus.PENDING


# ---------------------------------------------------------------------------
# find_gap
#
# find_gap(ti) returns the index at which `ti` can be inserted into a sorted,
# non-overlapping schedule without moving any existing instance, or None if it
# overlaps something. Index i means "between schedule[i-1] and schedule[i]";
# 0 means before everything, len(schedule) means after everything.
#
# Boundaries are inclusive: tasks that merely touch (one ends exactly when the
# next begins) do NOT count as overlapping.
#
# Edge cases covered below:
#   - empty schedule
#   - fits before the first / after the last instance
#   - exact-touch boundaries (end == start) front, back, and in a middle gap
#   - overlap with the first, last, and a middle instance
#   - a gap that is exactly the right size, and one that is one minute too small
#   - a ti that fully envelops an existing instance
#   - a zero-duration ti
# ---------------------------------------------------------------------------

DAY = dt.date(2026, 7, 4)


def at(hour, minute=0):
    """A datetime at the given time on the fixed test day."""
    return dt.datetime.combine(DAY, dt.time(hour, minute))


def inst(start, end):
    """A TaskInstance spanning [start, end). task_ref is unused by find_gap."""
    return TaskInstance(1, 1, None, start, end)


def sched(*spans):
    """A Scheduler whose schedule holds instances for the given (start, end) spans."""
    s = Scheduler()
    s.schedule = [inst(a, b) for a, b in spans]
    return s


def test_find_gap_empty_schedule():
    assert sched().find_gap(inst(at(9), at(10))) == 0


def test_find_gap_before_first():
    s = sched((at(9), at(10)))
    assert s.find_gap(inst(at(7), at(8))) == 0


def test_find_gap_touching_before_first():
    # ti ends exactly when the first instance starts -> still fits before it.
    s = sched((at(9), at(10)))
    assert s.find_gap(inst(at(8), at(9))) == 0


def test_find_gap_after_last():
    s = sched((at(9), at(10)))
    assert s.find_gap(inst(at(11), at(12))) == 1


def test_find_gap_touching_after_last():
    # ti starts exactly when the last instance ends -> fits after it.
    s = sched((at(9), at(10)))
    assert s.find_gap(inst(at(10), at(11))) == 1


def test_find_gap_overlaps_only_instance():
    s = sched((at(9), at(11)))
    assert s.find_gap(inst(at(10), at(12))) is None


def test_find_gap_identical_span_overlaps():
    s = sched((at(9), at(11)))
    assert s.find_gap(inst(at(9), at(11))) is None


def test_find_gap_middle_gap():
    s = sched((at(8), at(9)), (at(12), at(13)))
    assert s.find_gap(inst(at(10), at(11))) == 1


def test_find_gap_middle_gap_exact_fit():
    # Gap is 09:00-10:00; a 1-hour task touches both boundaries exactly.
    s = sched((at(8), at(9)), (at(10), at(11)))
    assert s.find_gap(inst(at(9), at(10))) == 1


def test_find_gap_middle_gap_one_minute_too_big():
    # Same gap, but the task runs one minute into the next instance -> overlap.
    s = sched((at(8), at(9)), (at(10), at(11)))
    assert s.find_gap(inst(at(9), at(10, 1))) is None


def test_find_gap_overlaps_first_of_many():
    s = sched((at(8), at(10)), (at(12), at(13)))
    assert s.find_gap(inst(at(9), at(9, 30))) is None


def test_find_gap_overlaps_last_of_many():
    s = sched((at(8), at(9)), (at(12), at(14)))
    assert s.find_gap(inst(at(13), at(15))) is None


def test_find_gap_envelops_existing_instance():
    # ti fully contains the second instance -> overlaps it.
    s = sched((at(8), at(9)), (at(11), at(12)), (at(14), at(15)))
    assert s.find_gap(inst(at(10), at(13))) is None


def test_find_gap_zero_duration_in_gap():
    # A zero-length instant inside a gap fits.
    s = sched((at(8), at(9)), (at(12), at(13)))
    assert s.find_gap(inst(at(10), at(10))) == 1


# ---------------------------------------------------------------------------
# fit_with_delay
#
# fit_with_delay(ti) tries to place `ti` LATER than its ideal start, by slotting
# it immediately after a scheduled instance. It scans forward from the first
# instance ending after ti.start and, for each, considers the gap after it:
#   - if that gap is smaller than ti's duration, it skips to the next instance;
#   - else, if the resulting delay (new_start - ideal_start) is within the task's
#     flexibility, it MUTATES ti.start/ti.end to the delayed slot and returns the
#     insertion index (i + 1);
#   - else (gap is big enough but the delay exceeds flexibility) it returns None.
# The slot after the last instance has an effectively infinite gap, so an append
# is only ever blocked by flexibility, never by size.
#
# Unlike find_gap, this reads ti.task_ref, so these instances need a real Task.
#
# Edge cases covered:
#   - delay into the immediately-following gap, within flexibility
#   - skipping a too-small gap to land in a later one
#   - delay exactly equal to flexibility (inclusive boundary)
#   - gap exactly equal to the duration (inclusive boundary)
#   - delay exceeding flexibility -> None, and ti left unmutated
#   - appending after the last instance
#   - no instance ends after ti.start -> None
#   - ti.start before every instance's end -> 1
# ---------------------------------------------------------------------------


def make_ti(ideal_start, duration, flexibility):
    """A TaskInstance whose task carries the duration/flexibility fit_with_delay needs."""
    task = Task(
        "t", None, ideal_start, duration, dt.timedelta(days=1),
        TaskType.WALK, Priority.MED, flexibility,
    )
    return TaskInstance(1, 1, task, ideal_start, ideal_start + duration)


def test_fit_delay_into_following_gap():
    # ti (ideal 09:30, 30 min) overlaps the 09:00-10:00 task; it should be
    # pushed to 10:00, into the 10:00-12:00 gap, a 30 min delay within flex.
    s = sched((at(8), at(9)), (at(9), at(10)), (at(12), at(13)))
    ti = make_ti(at(9, 30), dt.timedelta(minutes=30), dt.timedelta(hours=3))

    idx = s.fit_with_delay(ti)

    assert idx == 2
    assert ti.start == at(10)
    assert ti.end == at(10, 30)


def test_fit_delay_skips_too_small_gap():
    # The gap after the 09:00-10:00 task (10:00-10:20) is only 20 min, too small
    # for a 30 min task, so fit_with_delay skips it and lands in the next gap.
    s = sched((at(8), at(9)), (at(9), at(10)), (at(10, 20), at(11)), (at(13), at(14)))
    ti = make_ti(at(9, 30), dt.timedelta(minutes=30), dt.timedelta(hours=5))

    idx = s.fit_with_delay(ti)

    assert idx == 3
    assert ti.start == at(11)
    assert ti.end == at(11, 30)


def test_fit_delay_flexibility_boundary_inclusive():
    # Delay is exactly 2h and flexibility is exactly 2h -> still placed (<=).
    s = sched((at(8), at(9)), (at(9), at(11)))
    ti = make_ti(at(9), dt.timedelta(minutes=30), dt.timedelta(hours=2))

    idx = s.fit_with_delay(ti)

    assert idx == 2
    assert ti.start == at(11)


def test_fit_delay_gap_exactly_duration():
    # The gap (10:00-10:30) is exactly the duration (30 min) -> fits (gap < dur is False).
    s = sched((at(8), at(9)), (at(9), at(10)), (at(10, 30), at(11)))
    ti = make_ti(at(9, 30), dt.timedelta(minutes=30), dt.timedelta(hours=5))

    idx = s.fit_with_delay(ti)

    assert idx == 2
    assert ti.start == at(10)


def test_fit_delay_exceeds_flexibility_returns_none():
    # The only big-enough slot requires a 2h delay but flexibility is 1h -> None.
    # On the None branch ti must be left untouched.
    s = sched((at(8), at(9)), (at(9), at(11)))
    ti = make_ti(at(9), dt.timedelta(minutes=30), dt.timedelta(hours=1))

    idx = s.fit_with_delay(ti)

    assert idx is None
    assert ti.start == at(9)          # unmutated
    assert ti.end == at(9, 30)        # unmutated


def test_fit_delay_appends_after_last_instance():
    # ti (ideal 10:00) overlaps the last task (09:00-11:00); the only slot is
    # after it, where the gap is effectively infinite -> placed at 11:00.
    s = sched((at(8), at(9)), (at(9), at(11)))
    ti = make_ti(at(10), dt.timedelta(minutes=30), dt.timedelta(hours=3))

    idx = s.fit_with_delay(ti)

    assert idx == 2                   # == len(schedule): appended at the end
    assert ti.start == at(11)
    assert ti.end == at(11, 30)


def test_fit_delay_no_instance_after_start_returns_none():
    # Nothing ends after ti.start (ti.start is at/after the last end), so there
    # is no instance to delay past and the scan range is empty -> None.
    s = sched((at(8), at(9)))
    ti = make_ti(at(9), dt.timedelta(minutes=30), dt.timedelta(hours=3))

    assert s.fit_with_delay(ti) is None


def test_fit_delay_start_before_all_ends():
    # ti (ideal 10:00) overlaps the only task (09:00-11:00). The back-scan stops
    # at b_i == -1 (guarded), so ti is delayed to 11:00 and inserted at index 1.
    s = sched((at(9), at(11)))
    ti = make_ti(at(10), dt.timedelta(minutes=30), dt.timedelta(hours=3))

    idx = s.fit_with_delay(ti)

    assert idx == 1
    assert ti.start == at(11)


# ---------------------------------------------------------------------------
# extract_conflicts
#
# extract_conflicts(ti) removes from the schedule every instance that BOTH
# overlaps ti AND is strictly lower priority than ti, and returns those removed
# instances. Instances that merely touch ti (end == start) do not overlap.
#
# Priority is an enum where a LARGER .value means LOWER priority
# (HIGH=1, MED=2, LOW=3), so "curr is lower priority than ti" is
# curr.priority.value > ti.priority.value (strict — equal priority is kept).
#
# The schedule is scanned back-to-front and matches are popped as found, so the
# returned list is in REVERSE schedule order, and non-conflicting instances keep
# their relative order in the (now shorter) schedule.
#
# Both ti and the scheduled instances must carry a real Task (for .priority).
#
# Edge cases covered:
#   - empty schedule
#   - overlap but equal priority (kept) / higher priority (kept)
#   - a single lower-priority overlap (removed)
#   - touching boundary (not an overlap, kept)
#   - several lower-priority overlaps (all removed, reverse order)
#   - a mix of overlap/priority/non-overlap (only the right ones removed,
#     survivors keep order)
#   - a zero-duration ti inside a lower-priority interval
# ---------------------------------------------------------------------------


def pinst(start, end, priority):
    """A TaskInstance carrying a Task with the given priority (for extract_conflicts)."""
    task = Task(
        "t", None, start, end - start, dt.timedelta(days=1),
        TaskType.WALK, priority, dt.timedelta(hours=1),
    )
    return TaskInstance(1, 1, task, start, end)


def psched(*spans):
    """A Scheduler whose schedule holds (start, end, priority) instances."""
    s = Scheduler()
    s.schedule = [pinst(a, b, p) for a, b, p in spans]
    return s


def test_extract_conflicts_empty_schedule():
    s = psched()
    ti = pinst(at(9), at(10), Priority.HIGH)
    assert s.extract_conflicts(ti) == []
    assert s.schedule == []


def test_extract_conflicts_no_overlap_kept():
    s = psched((at(8), at(9), Priority.LOW))
    ti = pinst(at(10), at(11), Priority.HIGH)
    assert s.extract_conflicts(ti) == []
    assert len(s.schedule) == 1


def test_extract_conflicts_single_lower_priority_removed():
    s = psched((at(9), at(11), Priority.LOW))
    ti = pinst(at(10), at(10, 30), Priority.HIGH)

    conflicts = s.extract_conflicts(ti)

    assert len(conflicts) == 1
    assert conflicts[0].start == at(9)
    assert s.schedule == []


def test_extract_conflicts_equal_priority_kept():
    # Strictly lower priority is required; equal priority overlaps are left alone.
    s = psched((at(9), at(11), Priority.MED))
    ti = pinst(at(10), at(10, 30), Priority.MED)

    assert s.extract_conflicts(ti) == []
    assert len(s.schedule) == 1


def test_extract_conflicts_higher_priority_kept():
    # The overlapping instance outranks ti, so it is not evicted.
    s = psched((at(9), at(11), Priority.HIGH))
    ti = pinst(at(10), at(10, 30), Priority.LOW)

    assert s.extract_conflicts(ti) == []
    assert len(s.schedule) == 1


def test_extract_conflicts_touching_boundary_kept():
    # ti starts exactly when the lower-priority instance ends -> not an overlap.
    s = psched((at(8), at(9), Priority.LOW))
    ti = pinst(at(9), at(10), Priority.HIGH)

    assert s.extract_conflicts(ti) == []
    assert len(s.schedule) == 1


def test_extract_conflicts_multiple_removed_in_reverse_order():
    # ti overlaps two lower-priority instances; both are removed and returned
    # in reverse schedule order (back-to-front scan).
    s = psched(
        (at(9), at(10), Priority.LOW),
        (at(10, 30), at(11, 30), Priority.MED),
    )
    ti = pinst(at(9, 30), at(11), Priority.HIGH)

    conflicts = s.extract_conflicts(ti)

    assert [c.start for c in conflicts] == [at(10, 30), at(9)]
    assert s.schedule == []


def test_extract_conflicts_mixed_survivors_keep_order():
    # Only the overlapping lower-priority instance (09:00-10:00, LOW) is removed.
    # The HIGH overlap, the non-overlapping HIGH, and the non-overlapping LOW stay
    # in their original relative order.
    s = psched(
        (at(8), at(9), Priority.HIGH),       # no overlap
        (at(9), at(10), Priority.LOW),       # overlap + lower -> removed
        (at(10), at(11), Priority.HIGH),     # overlap but higher -> kept
        (at(12), at(13), Priority.LOW),      # no overlap
    )
    ti = pinst(at(9, 30), at(11, 30), Priority.MED)

    conflicts = s.extract_conflicts(ti)

    assert [c.start for c in conflicts] == [at(9)]
    assert [c.start for c in s.schedule] == [at(8), at(10), at(12)]


def test_extract_conflicts_zero_duration_ti_inside_interval():
    # A zero-length ti strictly inside a lower-priority interval still overlaps it.
    s = psched((at(9), at(11), Priority.LOW))
    ti = pinst(at(10), at(10), Priority.HIGH)

    conflicts = s.extract_conflicts(ti)

    assert len(conflicts) == 1
    assert s.schedule == []


# ---------------------------------------------------------------------------
# Scheduler.mark_complete
#
# mark_complete(ti, status):
#   - sets ti.status = status (mutates the instance passed in);
#   - builds a SUCCESSOR TaskInstance one interval later:
#       start = ti.start + ti.task_ref.interval
#       end   = start + ti.task_ref.duration
#     copying pet_id / task_id / task_ref and defaulting to PENDING;
#   - inserts that successor into the schedule.
# It does NOT remove ti from the schedule, so the schedule grows by one (the
# completed instance stays, now marked, alongside its successor).
#
# Edge cases covered:
#   - a daily task -> successor falls on the following day (the headline case)
#   - ti.status reflects the status passed in
#   - the successor copies identifiers and starts out PENDING
#   - a non-DONE status (MISSED) still spawns a successor
#   - a weekly interval -> successor 7 days later
#   - a sub-day interval (12h) -> successor the SAME day (not hard-coded to +1 day)
#   - successor start/end derive from interval + duration (independent of how
#     late the instance was actually completed)
# ---------------------------------------------------------------------------


def sched_ti(start, *, duration=dt.timedelta(minutes=30), interval=dt.timedelta(days=1),
             priority=Priority.MED, flexibility=dt.timedelta(hours=1)):
    """A TaskInstance whose Task carries the interval/duration mark_complete needs."""
    task = Task("t", None, start, duration, interval, TaskType.WALK, priority, flexibility)
    return TaskInstance(1, 1, task, start, start + duration)


def successor_of(scheduler, ti):
    """The single instance in the schedule that isn't ti itself."""
    others = [x for x in scheduler.schedule if x is not ti]
    assert len(others) == 1
    return others[0]


def test_mark_complete_daily_task_creates_next_day_instance():
    # Headline behavior: completing a daily task schedules it again the next day.
    ti = sched_ti(at(8), interval=dt.timedelta(days=1))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)

    assert len(s.schedule) == 2          # original stays + successor added
    new = successor_of(s, ti)
    assert new.start == at(8) + dt.timedelta(days=1)
    assert new.start.date() == DAY + dt.timedelta(days=1)
    assert new.end == new.start + dt.timedelta(minutes=30)


def test_mark_complete_sets_status_on_original():
    ti = sched_ti(at(8))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)

    assert ti.status == TaskStatus.DONE


def test_mark_complete_successor_copies_identifiers_and_is_pending():
    ti = sched_ti(at(8))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)
    new = successor_of(s, ti)

    assert new.pet_id == ti.pet_id
    assert new.task_id == ti.task_id
    assert new.task_ref is ti.task_ref
    assert new.status == TaskStatus.PENDING   # successor starts fresh


def test_mark_complete_non_done_status_still_creates_successor():
    # A missed (or skipped) occurrence is still rescheduled for next time.
    ti = sched_ti(at(8), interval=dt.timedelta(days=1))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.MISSED)

    assert ti.status == TaskStatus.MISSED
    new = successor_of(s, ti)
    assert new.start == at(8) + dt.timedelta(days=1)


def test_mark_complete_weekly_interval():
    ti = sched_ti(at(8), interval=dt.timedelta(weeks=1))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)
    new = successor_of(s, ti)

    assert new.start == at(8) + dt.timedelta(days=7)
    assert new.start.date() == DAY + dt.timedelta(days=7)


def test_mark_complete_sub_day_interval_same_day():
    # A 12-hour interval lands the successor later the SAME day -- mark_complete
    # adds task.interval, it does not assume a daily cadence.
    ti = sched_ti(at(8), interval=dt.timedelta(hours=12))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)
    new = successor_of(s, ti)

    assert new.start == at(20)
    assert new.start.date() == DAY


def test_mark_complete_successor_timing_independent_of_actual_completion():
    # mark_complete takes no completion time; the successor is always
    # ti.start + interval, regardless of when "done" was recorded.
    ti = sched_ti(at(8), duration=dt.timedelta(minutes=45), interval=dt.timedelta(days=1))
    s = Scheduler()
    s.insert(ti)

    s.mark_complete(ti, TaskStatus.DONE)
    new = successor_of(s, ti)

    assert new.start == at(8) + dt.timedelta(days=1)
    assert new.end == new.start + dt.timedelta(minutes=45)