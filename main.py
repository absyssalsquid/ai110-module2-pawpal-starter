from pawpal_system import * 

app = App()
app.owner.name = "Wilfred"

eoin  = app.owner.addPet(Pet('Eoin', 'bird', 'crow', dt.datetime(year=2022, month=1, day=14)))
hans  = app.owner.addPet(Pet('Hans', 'dog', 'husky', dt.datetime(year=2023, month=6, day=2)))
henry = app.owner.addPet(Pet('Henry', 'cat', None, dt.datetime(year=2023, month=8, day=2)))

dailies = [
    [hans, 'Morning walk', None, dt.time(hour=6, minute=30), dt.timedelta(minutes=45), dt.timedelta(days=1), TaskType.WALK, DEFAULT_PF[TaskType.WALK]['priority'], DEFAULT_PF[TaskType.WALK]['flexibility']],
    [hans, 'Morning feed', None, dt.time(hour=7, minute=15), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [henry, 'Morning feed', None, dt.time(hour=7, minute=20), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [eoin, 'Morning feed', None, dt.time(hour=7, minute=25), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [eoin, 'Meds', None, dt.time(hour=7, minute=30), dt.timedelta(minutes=10), dt.timedelta(hours=12), TaskType.MEDS, DEFAULT_PF[TaskType.MEDS]['priority'], DEFAULT_PF[TaskType.MEDS]['flexibility']],
    [eoin, 'Afternoon snack', None, dt.time(hour=14, minute=0), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [henry, 'Afternoon snack', None, dt.time(hour=14, minute=5), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [henry, 'Evening feed', None, dt.time(hour=17, minute=0), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [hans, 'Evening feed', None, dt.time(hour=17, minute=5), dt.timedelta(minutes=5), dt.timedelta(days=1), TaskType.FEEDING, DEFAULT_PF[TaskType.FEEDING]['priority'], DEFAULT_PF[TaskType.FEEDING]['flexibility']],
    [henry, 'Clean litter box', None, dt.time(hour=20, minute=0), dt.timedelta(minutes=10), dt.timedelta(days=1), TaskType.CLEANING, DEFAULT_PF[TaskType.CLEANING]['priority'], DEFAULT_PF[TaskType.CLEANING]['flexibility']],
]

today = dt.date.today()
for chore in dailies:
    chore[3] = dt.datetime.combine(today, chore[3])
    task = Task(*chore[1:])
    pet_id = chore[0]
    app.addTask(pet_id, task)

app.addTask(eoin, Task(
    'Clean cage', None, 
    dt.datetime(year=2026, month=7, day=4, hour=9, minute=0),
    dt.timedelta(hours=1),
    dt.timedelta(weeks=4), 
    TaskType.GROOMING, 
    DEFAULT_PF[TaskType.GROOMING]['priority'],
    DEFAULT_PF[TaskType.GROOMING]['flexibility']
))
app.addTask(hans, Task(
    'Brush fur', None, 
    dt.datetime(year=2026, month=7, day=4, hour=10, minute=0),
    dt.timedelta(minutes=30),
    dt.timedelta(weeks=1), 
    TaskType.GROOMING, 
    DEFAULT_PF[TaskType.GROOMING]['priority'],
    DEFAULT_PF[TaskType.GROOMING]['flexibility']
))
app.addTask(hans, Task(
    'Brush teeth', None, 
    dt.datetime(year=2026, month=7, day=4, hour=10, minute=30),
    dt.timedelta(minutes=15),
    dt.timedelta(weeks=1), 
    TaskType.GROOMING, 
    DEFAULT_PF[TaskType.GROOMING]['priority'],
    DEFAULT_PF[TaskType.GROOMING]['flexibility']
))
app.addTask(hans, Task(
    'Bath', None, 
    dt.datetime(year=2026, month=7, day=4, hour=14, minute=0),
    dt.timedelta(hours=1),
    dt.timedelta(weeks=4), 
    TaskType.GROOMING, 
    DEFAULT_PF[TaskType.GROOMING]['priority'],
    DEFAULT_PF[TaskType.GROOMING]['flexibility']
))

app.scheduler.printSchedule(app.owner)

print("\nmark 5 tasks as complete")
for ti in app.scheduler.schedule[:5]:
    app.scheduler.mark_complete(app.owner, ti, TaskStatus.DONE)

app.scheduler.printSchedule(app.owner)
