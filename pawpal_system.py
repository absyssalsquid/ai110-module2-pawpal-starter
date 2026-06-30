import sys
sys.stdout.reconfigure(encoding='utf-8')

import datetime as dt
from enum import Enum

class TaskType(Enum):
    MEDS = 1
    FEEDING = 2
    WALK = 3
    GROOMING = 4
    CLEANING = 4

class Priority(Enum):
    HIGH = 1
    MED = 2
    LOW = 3

class TaskStatus(Enum):
    PENDING = 1
    DONE = 2
    SKIPPED = 3
    MISSED = 4

DEFAULT_PF = {
    TaskType.MEDS: {
        'priority': Priority.HIGH,
        'flexibility': dt.timedelta(hours=1)
    },
    TaskType.FEEDING: {
        'priority': Priority.HIGH,
        'flexibility': dt.timedelta(hours=2)
    },
    TaskType.WALK: {
        'priority': Priority.MED,
        'flexibility': dt.timedelta(hours=3)
    },
    TaskType.CLEANING: {
        'priority': Priority.MED,
        'flexibility': dt.timedelta(days=1)
    },
    TaskType.GROOMING: {
        'priority': Priority.LOW,
        'flexibility': dt.timedelta(days=5)
    }
}

class Task:
    """A recurring care activity (the definition, not a single occurrence)."""

    def __init__(
        self,
        name: str,
        desc: str,
        ideal_start_time: dt.datetime,
        duration: dt.timedelta,
        interval: dt.timedelta,

        type: TaskType,
        priority: Priority,
        flexibility: dt.timedelta,
    ):
        self.name = name
        self.desc = desc
        self.ideal_start_time = ideal_start_time
        self.duration = duration
        self.interval = interval
        
        self.type = type
        self.priority = priority
        self.flexibility = flexibility

        self.active = True

class Pet:
    """Stores pet details and its tasks, keyed by a per-pet task id."""

    def __init__(
        self,
        name: str,
        species: str,
        breed: str,
        dob: dt.datetime,
        active: bool = True,
    ):
        self.name = name
        self.species = species
        self.breed = breed
        self.dob = dob
        self.active = active
        self.tasks: dict[int, Task] = {}

        self.next_id = 1

    def addTask(self, task: Task) -> None:
        """Store a task under a new per-pet id and return that id."""
        id = self.next_id
        self.tasks[id] = task
        self.next_id += 1
        return id

    def removeTask(self, taskID: int) -> None:
        """Delete the task with the given id from this pet."""
        del self.tasks[taskID]

    def deactivateTask(self, taskID: int) -> None:
        """Mark the task with the given id as inactive."""
        self.tasks_by_id[taskID].active = False

class Owner:
    """The single app user. Manages pets and provides access to their tasks."""

    def __init__(self, name: str = None):
        self.name = name
        self.pets: dict[int, Pet] = {}

        self.next_id = 1

    def getTask(self, pet_id, task_id):
        """Return the task with task_id belonging to the pet with pet_id."""
        return self.pets[pet_id].tasks[task_id]

    def addPet(self, pet : Pet) -> None:
        """Store a pet under a new id and return that id."""
        id = self.next_id
        self.pets[id] = pet
        self.next_id += 1
        return id

    def removePet(self, petID: int) -> None:
        """Delete the pet with the given id from this owner."""
        del self.pets[petID]

    def deactivatePet(self, petID: int) -> None:
        """Mark the pet with the given id as inactive."""
        self.pets_by_id[petID].active = False

class TaskInstance:
    """A single day's occurrence of a Task. Identified by (pet_id, task_id)."""

    CHECKMARKS = {
        TaskStatus.PENDING: ' ',
        TaskStatus.DONE: 'o',
        TaskStatus.SKIPPED: '-',
        TaskStatus.MISSED: 'x'
    }

    def __init__(
        self,
        pet_id: int,
        task_id: int,
        start: dt.datetime,
        end: dt.datetime
    ):
        self.pet_id = pet_id
        self.task_id = task_id
        self.start = start
        self.end = end

        self.status = TaskStatus.PENDING
        self.completed_at: dt.datetime = None
        self.notes = ""

    def toString(self, owner: Owner, with_date=False):
        """Render this instance as a one-line status string for printing."""
        pet = owner.pets[self.pet_id]
        task = pet.tasks[self.task_id]

        check = TaskInstance.CHECKMARKS[self.status]
        date = self.start.date() if with_date else ''
        return f" {check} {date} {self.start.time()} - {self.end.time()} | {pet.name} - {task.name}"

class Scheduler:
    """The 'brain': organizes tasks across pets into a daily schedule."""

    def __init__(self):
        self.schedule: list[TaskInstance] = []
        self.unscheduled: list[TaskInstance] = []

    def mark_complete(self, owner: Owner, ti: TaskInstance, status: TaskStatus, mark_time: dt.datetime=None):
        """Set a task instance's status and schedule its next occurrence."""
        if mark_time:
            completion_time = mark_time
        else:
            completion_time = ti.end

        # mark old task instance
        ti.status = status
        ti.completed_at = completion_time

        # make new task instance
        task = owner.getTask(ti.pet_id, ti.task_id)
        delay = completion_time - ti.end

        start_time = ti.start + delay + task.interval
        end_time = start_time + task.duration

        new_ti = TaskInstance(ti.pet_id, ti.task_id, start_time, end_time)
        self.insert(new_ti)

    def insert(self, ti: TaskInstance):
        """Place a task instance into the first non-conflicting schedule slot."""
        if len(self.schedule) == 0:
            self.schedule.insert(0, ti)
            return

        if ti.end <= self.schedule[0].start:
            self.schedule.insert(0, ti)
            return

        if ti.start >= self.schedule[-1].end:
            self.schedule.insert(len(self.schedule), ti)
            return
        
        for i in range(len(self.schedule)-1, 0, -1): # go backwards
            before = self.schedule[i-1]
            after = self.schedule[i]
            if before.end <= ti.start and ti.end <= after.start:
                self.schedule.insert(i, ti)
                return
        
            # if before.start <= ti.start and ti.end <= after.end:
        # shift tasks

        self.unscheduled.append(ti)
    
    def printSchedule(self, owner: Owner):
        """Print the schedule grouped by date, plus any unscheduled tasks."""
        print(f"Schedule for {owner.name}")
        for i in range(len(self.schedule)):
            ti = self.schedule[i]
            if i == 0: 
                print(ti.start.date())
            else:
                curr_date = self.schedule[i  ].start.date()
                prev_date = self.schedule[i-1].start.date()
                if curr_date != prev_date:
                    print()
                    print(curr_date)

            print(ti.toString(owner))

        if len(self.unscheduled) > 0:
            print('could not schedule')
            for ti in self.unscheduled:
                print(ti.toString(owner, with_date=True))

class App:
    """Application root holding the owner and the scheduler."""

    def __init__(self):
        self.owner = Owner()
        self.scheduler = Scheduler()

    def addTask(self, pet_id, task:Task):
        """Add a task to a pet and insert its first instance into the schedule."""
        task_id = self.owner.pets[pet_id].addTask(task)

        start_time = task.ideal_start_time 
        end_time = start_time + task.duration

        ti = TaskInstance(pet_id, task_id, start_time, end_time)
        self.scheduler.insert(ti)