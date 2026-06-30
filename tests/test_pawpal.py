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

