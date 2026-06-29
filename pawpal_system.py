from enum import Enum
import deque
import datetime

class TaskType(Enum):
    MEDS = 1
    FEEDING = 2
    WALK = 3
    BATH = 3

class Priority(Enum):
    LOW = 1
    MED = 2
    HIGH = 3

class TaskStatus(Enum):
    PENDING = 1
    DONE = 2
    SKIPPED = 3
    MISSED = 4

DEFAULT_PRIORITY = {
    TaskType.MEDS: {
        'priority': Priority.HIGH,
        'flexibility': datetime.timedelta(minutes=30)
    },
    TaskType.FEEDING: {
        'priority': Priority.HIGH,
        'flexibility': datetime.timedelta(hours=1)
    },
    TaskType.WALK: {
        'priority': Priority.MED,
        'flexibility': datetime.timedelta(hours=2)
    },
    TaskType.BATH: {
        'priority': Priority.LOW,
        'flexibility': datetime.timedelta(days=3)
    }
}


class Task:
    """A recurring care activity (the definition, not a single occurrence)."""

    def __init__(
        self,
        name: str,
        desc: str,
        ideal_start_time: datetime.time,
        flexibility: datetime.timedelta,
        duration: datetime.timedelta,
        frequency: datetime.timedelta,
        type: TaskType,
        priority: Priority,
    ):
        self.name = name
        self.desc = desc
        self.ideal_start_time = ideal_start_time
        self.flexibility = flexibility
        self.duration = duration
        self.frequency = frequency
        self.type = type
        self.priority = priority


class TaskInstance:
    """A single day's occurrence of a Task. Identified by (pet_id, task_id)."""

    def __init__(
        self,
        pet_id: int,
        task_id: int,
        scheduled_time: datetime.datetime,
        status: TaskStatus = TaskStatus.PENDING,
        notes: str = "",
    ):
        self.pet_id = pet_id
        self.task_id = task_id
        self.scheduled_time = scheduled_time
        self.status = status
        self.notes = notes


class Pet:
    """Stores pet details and its tasks, keyed by a per-pet task id."""

    def __init__(
        self,
        name: str,
        species: str,
        breed: str,
        dob: datetime.datetime,
        color: str,
        active: bool = True,
    ):
        self.name = name
        self.species = species
        self.breed = breed
        self.dob = dob
        self.color = color
        self.active = active
        self.tasks_by_id: dict[int, Task] = {}

        self.next_id = 1

    def add(self, task: Task) -> None:
        pass

    def remove(self, taskID: int) -> None:
        pass

class Owner:
    """The single app user. Manages pets and provides access to their tasks."""

    def __init__(self, name: str):
        self.name = name
        self.pets_by_id: dict[int, Pet] = {}

        self.next_id = 1

    def add(self, pet : Pet) -> None:
        pass

    def remove(self, petID: int) -> None:
        pass


class Scheduler:
    """The 'brain': organizes tasks across pets into a daily schedule."""

    def __init__(self):
        self.schedule: list[TaskInstance] = []

    def generate(self, owner: Owner) -> list[TaskInstance]:
        pass


class App:
    """Application root holding the owner and the scheduler."""

    def __init__(self, owner: Owner, scheduler: Scheduler):
        self.owner = owner
        self.scheduler = scheduler