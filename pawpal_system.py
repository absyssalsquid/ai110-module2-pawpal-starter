import sys
sys.stdout.reconfigure(encoding='utf-8')

import datetime as dt
from enum import Enum

class TaskType(Enum):
    MEDS = 1
    FEEDING = 2
    WALK = 3
    GROOMING = 4
    CLEANING = 5
    OTHER = 6

class Priority(Enum):
    HIGH = 1
    MED = 2
    LOW = 3

class TaskStatus(Enum):
    PENDING = 1
    DONE = 2
    MISSED = 3

def format_interval(td: dt.timedelta) -> str:
    """Format a timedelta as a human-readable string.

    If only one time component is non-zero, show just that component.
    Otherwise, show the full timedelta string.

    Examples:
        28 days → "28 days"
        1 day → "1 day"
        12 hours → "12 hrs"
        1 hour → "1 hr"
        5 minutes → "5 min"
        1 day 2 hours → str(td)
    """
    days = td.days
    seconds = td.seconds

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    components = [
        (days, 'day', 'days'),
        (hours, 'hr', 'hrs'),
        (minutes, 'min', 'min'),
        (secs, 'sec', 'sec'),
    ]
    non_zero = [c for c in components if c[0] != 0]

    if len(non_zero) == 1:
        val, sing, plur = non_zero[0]
        unit = sing if val == 1 else plur
        return f"{val} {unit}"

    return str(td)


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

    def deleteTask(self, task_id: int) -> None:
        """Delete the task with the given id from this pet."""
        del self.tasks[task_id]

    def deactivateTask(self, task_id: int) -> None:
        """Mark the task with the given id as inactive."""
        self.tasks[task_id].active = False

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

    def deletePet(self, pet_id: int) -> None:
        """Delete the pet with the given id from this owner."""
        del self.pets[pet_id]

    def deactivatePet(self, pet_id: int) -> None:
        """Mark the pet with the given id as inactive."""
        self.pets[pet_id].active = False

class TaskInstance:
    """A single day's occurrence of a Task. Identified by (pet_id, task_id)."""

    CHECKMARKS = {
        TaskStatus.PENDING: ' ',
        TaskStatus.DONE: 'o',
        TaskStatus.MISSED: 'x'
    }

    def __init__(
        self,
        pet_id: int,
        task_id: int,
        task_ref: Task,
        start: dt.datetime,
        end: dt.datetime
    ):
        self.pet_id = pet_id
        self.task_id = task_id
        self.task_ref = task_ref
        self.start = start
        self.end = end
        self.ideal_start = start

        self.status = TaskStatus.PENDING
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

    def mark_complete(self, ti: TaskInstance, status: TaskStatus):
        """Set a task instance's status and schedule its next occurrence."""
        ti.status = status

        # make new task instance
        task = ti.task_ref
        start_time = ti.start + task.interval
        end_time = start_time + task.duration

        new_ti = TaskInstance(ti.pet_id, ti.task_id, task, start_time, end_time)
        self.insert(new_ti)

    def find_gap(self, ti: TaskInstance) -> int | None:
        """Find a gap where ti fits without moving other tasks. Return insertion index or None."""
        if not self.schedule:
            return 0
        if ti.end <= self.schedule[0].start:
            return 0
        if ti.start >= self.schedule[-1].end:
            return len(self.schedule)
        
        for i in range(len(self.schedule)-1, 0, -1): # go backwards to ignore possibly long history
            before = self.schedule[i-1]
            after = self.schedule[i]
            if before.end <= ti.start and ti.end <= after.start:
                return i
        return None

    def fit_with_delay(self, ti: TaskInstance) -> int | None:
        """Try to fit ti by shifting its start time within flexibility bounds. Return insertion index or None."""
        b_i = len(self.schedule)-1
        while (self.schedule[b_i].end > ti.start) and b_i >= 0:
            b_i -= 1

        for i in range(b_i+1, len(self.schedule)):
            before = self.schedule[i]
            new_start = before.end
            delay = new_start - ti.ideal_start

            gap = dt.timedelta(days=999) \
                if i+1 >= len(self.schedule) \
                else self.schedule[i+1].start - before.end
            if gap < ti.task_ref.duration: continue # cant fit task in gap

            if delay <= ti.task_ref.flexibility: 
                ti.start, ti.end = new_start, new_start + ti.task_ref.duration
                return i+1
            else:
                return None
    
    def extract_conflicts(self, ti:TaskInstance):
        # get events that overlap ti and are lower priority
        conflicts = []
        for i in range(len(self.schedule)-1, -1, -1):
            curr = self.schedule[i]
            overlaps = ti.start < curr.end and ti.end > curr.start
            lower_priority = curr.task_ref.priority.value > ti.task_ref.priority.value
            if overlaps and lower_priority:
                conflicts.append(self.schedule.pop(i))
        return conflicts

    def insert(self, ti: TaskInstance, pop_conflicts=True):
        """Place a task instance into a schedule slot."""
        idx = self.find_gap(ti)
        if idx is not None:
            self.schedule.insert(idx, ti)
            return

        if pop_conflicts:
            overlaps = [ti] + self.extract_conflicts(ti)
            overlaps.sort(key=lambda x: x.task_ref.priority.value)
            for oti in overlaps:
                self.insert(oti, pop_conflicts=False)
        
        else:
            # insert with delay
            # print("inserting with delay", ti.task_ref.name)
            idx = self.fit_with_delay(ti)
            if idx is not None:
                self.schedule.insert(idx, ti)
                return
            self.unscheduled.append(ti)
            return
    
    def filterPending(self):
        is_pending = lambda ti: ti.status.value == TaskStatus.PENDING.value
        pending   = [ti for ti in self.schedule if is_pending(ti)]
        completed = [ti for ti in self.schedule if not is_pending(ti)]
        return pending, completed

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

    def removePending(self, match_fn):
        is_pending = lambda ti: ti.status.value == TaskStatus.PENDING.value

        has_completed = False
        # remove all pending tasks that match
        for i in range(len(self.schedule)-1, -1, -1):
            ti = self.schedule[i]
            if match_fn(ti):
                if is_pending(ti): self.schedule.pop(i)
                else: has_completed = True

        for i in range(len(self.unscheduled)-1, -1, -1):
            ti = self.schedule[i]
            if match_fn(ti):
                if is_pending(ti): self.scheduler.unscheduled.pop(i)
                else: has_completed = True
        
        return has_completed

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

        ti = TaskInstance(pet_id, task_id, task, start_time, end_time)
        self.scheduler.insert(ti)
        
    def delete_task(self, pet_id, task_id):
        """Drop pending task instances from the scheduler."""
        match_fn = lambda ti: (ti.pet_id == pet_id and ti.task_id == task_id)
        can_delete = not self.scheduler.removePending(match_fn)

        if can_delete:
            self.owner.pets[pet_id].deleteTask(task_id)
        else:
            self.owner.pets[pet_id].deactivateTask(task_id)

    def deletePet(self, pet_id):
        """Drop pending task instances from the scheduler."""

        match_fn = lambda ti: (ti.pet_id == pet_id )
        can_delete = not self.scheduler.removePending(match_fn)

        if can_delete:
            print("deleting")
            self.owner.deletePet(pet_id)
        else:
            print("deactivating")
            self.owner.deactivatePet(pet_id)

        print("remaining pets")
        for id, pet in self.owner.pets.items():
            print(pet.name)
