import datetime as dt

import streamlit as st

from pawpal_system import *
from main import init_template
# =======================================================

st.session_state.setdefault('app', init_template())
st.session_state.setdefault('view', 'schedule')
st.session_state.setdefault('selected_pet_id', None)
st.session_state.setdefault('editing_pet', False)
st.session_state.setdefault('adding_task', False)
st.session_state.setdefault('editing_task_id', None)

app = st.session_state.app
owner = app.owner
sched = app.scheduler

# st.set_page_config(layout="wide")

# =======================================================
# Helpers for the task add/edit forms
# =======================================================

def split_flex(td):
    """Break a timedelta into (days, hours)."""
    total_h = td.total_seconds() / 3600
    days = int(total_h // 24)
    return days, int(round(total_h - days * 24))


def split_interval(td):
    """Break a timedelta into (weeks, days, hours)."""
    total_h = td.total_seconds() / 3600
    weeks = int(total_h // (24 * 7))
    rem = total_h - weeks * 24 * 7
    days = int(rem // 24)
    return weeks, days, int(round(rem - days * 24))


def seed_task_state(prefix, task=None):
    """Seed the widget state for a task form, from a task or from type defaults."""
    if task is None:
        t = list(TaskType)[0]
        d = DEFAULT_PF[t]
        flex_d, flex_h = split_flex(d['flexibility'])
        values = {
            'name': "", 'desc': "", 'type': t,
            'date': dt.date.today(), 'start_h': 8, 'start_min': 0,
            'dur': 30,
            'rep_weeks': 0, 'rep_days': 1, 'rep_hours': 0,
            'priority': d['priority'],
            'flex_days': flex_d, 'flex_hours': flex_h,
            'active': True,
        }
    else:
        flex_d, flex_h = split_flex(task.flexibility)
        rep_w, rep_d, rep_h = split_interval(task.interval)
        values = {
            'name': task.name, 'desc': task.desc or "", 'type': task.type,
            'date': task.ideal_start_time.date(),
            'start_h': task.ideal_start_time.hour, 'start_min': task.ideal_start_time.minute,
            'dur': int(task.duration.total_seconds() // 60),
            'rep_weeks': rep_w, 'rep_days': rep_d, 'rep_hours': rep_h,
            'priority': task.priority,
            'flex_days': flex_d, 'flex_hours': flex_h,
            'active': task.active,
        }
    for k, v in values.items():
        st.session_state[f"{prefix}_{k}"] = v


def sync_pf(prefix):
    """When the task type changes, reset priority and flexibility to its defaults."""
    d = DEFAULT_PF[st.session_state[f"{prefix}_type"]]
    flex_d, flex_h = split_flex(d['flexibility'])
    st.session_state[f"{prefix}_priority"] = d['priority']
    st.session_state[f"{prefix}_flex_days"] = flex_d
    st.session_state[f"{prefix}_flex_hours"] = flex_h


def render_task_fields(prefix):
    """Render the shared set of task input widgets, keyed by prefix."""
    st.text_input("Task name", key=f"{prefix}_name")
    st.text_input("Description", key=f"{prefix}_desc")

    c1, c2 = st.columns(2)
    c1.selectbox("Type", list(TaskType), key=f"{prefix}_type",
                 format_func=lambda t: t.name, on_change=sync_pf, args=(prefix,))
    c2.selectbox("Priority", list(Priority), key=f"{prefix}_priority",
                 format_func=lambda p: p.name)

    st.markdown("**Start time**")
    sd, sh, sm = st.columns(3)
    sd.date_input("Date", key=f"{prefix}_date")
    sh.number_input("Hour", min_value=0, max_value=23, key=f"{prefix}_start_h")
    sm.number_input("Minute", min_value=0, max_value=59, key=f"{prefix}_start_min")

    st.number_input("Duration (minutes)", min_value=1, max_value=480, key=f"{prefix}_dur")

    st.markdown("**Flexibility**")
    fd, fh = st.columns(2)
    fd.number_input("Days", min_value=0, max_value=31, key=f"{prefix}_flex_days")
    fh.number_input("Hours", min_value=0, max_value=23, key=f"{prefix}_flex_hours")

    st.markdown("**Repeat every**")
    rw, rd, rh = st.columns(3)
    rw.number_input("Weeks", min_value=0, max_value=52, key=f"{prefix}_rep_weeks")
    rd.number_input("Days", min_value=0, max_value=31, key=f"{prefix}_rep_days")
    rh.number_input("Hours", min_value=0, max_value=23, key=f"{prefix}_rep_hours")

    st.checkbox("Active", key=f"{prefix}_active")


def build_task(prefix):
    """Construct a Task from the widget state under prefix."""
    g = lambda k: st.session_state[f"{prefix}_{k}"]
    start = dt.datetime.combine(g('date'), dt.time(int(g('start_h')), int(g('start_min'))))
    return Task(
        g('name'),
        g('desc') or None,
        start,
        dt.timedelta(minutes=int(g('dur'))),
        dt.timedelta(weeks=int(g('rep_weeks')), days=int(g('rep_days')), hours=int(g('rep_hours'))),
        g('type'),
        g('priority'),
        dt.timedelta(days=int(g('flex_days')), hours=int(g('flex_hours'))),
    )

def ti_label(ti):
    """Return (pet_name, task_name) for a task instance."""
    pet = owner.pets[ti.pet_id]
    return pet.name, pet.tasks[ti.task_id].name


def seed_ti_state(ti):
    """Seed the schedule-instance edit widgets from a task instance."""
    comp = ti.end
    st.session_state.update({
        'eti_date': ti.start.date(), 'eti_h': ti.start.hour, 'eti_m': ti.start.minute,
        'eti_cdate': comp.date(), 'eti_ch': comp.hour, 'eti_cm': comp.minute,
    })

def render_schedule(data, empty_msg, key_prefix):
    """Render a list of task instances as a table with mark-complete / edit buttons.

    key_prefix keeps widget keys unique so the same table can be shown more than
    once on a page (e.g. upcoming vs. unscheduled) without colliding ids.
    """
    if data:
        widths = [1, 1.5, 3, 1, 1.5, 0.9, 0.9]
        head = st.columns(widths)
        for col, label in zip(head, ["Date", "Pet", "Task", "Time", "Duration"]):
            col.markdown(f"**{label}**")

        for i, ti in enumerate(data):
            pet_name, task_name = ti_label(ti)
            cols = st.columns(widths)

            if i==0:
                cols[0].write(ti.start.strftime("%m-%d"))

            if i > 0:
                curr_date = data[i  ].start.date()
                prev_date = data[i-1].start.date()
                if curr_date != prev_date:
                    cols[0].write(ti.start.strftime("%m-%d"))

            cols[1].write(pet_name)
            cols[2].write(task_name)
            cols[3].write(ti.start.strftime("%H:%M"))
            cols[4].write(format_interval(ti.task_ref.duration))
            if cols[5].button("✅", key=f"{key_prefix}_done_{i}", help="Mark done"):
                sched.mark_complete(ti, TaskStatus.DONE)
                st.rerun()
            if cols[6].button("❌", key=f"{key_prefix}_missed_{i}", help="Mark missed"):
                sched.mark_complete(ti, TaskStatus.MISSED)
                st.rerun()

    else:
        st.info(empty_msg)

def render_schedule_view():
    """Render the overall schedule: upcoming, unscheduled, and completed."""
    st.title("📅 Schedule")

    pending, completed = sched.filterPending()
    completed = completed[::-1]

    st.subheader("Upcoming")
    render_schedule(pending, "No upcoming tasks.", key_prefix="upcoming")

    st.divider()

    # ---- Unscheduled ----
    st.subheader("Unscheduled (conflict detected)")
    render_schedule(sched.unscheduled, "None.", key_prefix="unscheduled")

    # ---- Completed (reverse order, behind a dropdown) ----
    with st.expander(f"Completed ({len(completed)})"):
        if completed:
            widths = [3, 3, 3, 2, 2]
            head = st.columns(widths)
            for col, label in zip(head, ["Pet", "Task", "Date", "Time", "Status"]):
                col.markdown(f"**{label}**")
            for ti in completed:
                pet_name, task_name = ti_label(ti)
                cols = st.columns(widths)
                cols[0].write(pet_name)
                cols[1].write(task_name)
                cols[2].write(ti.start.strftime("%Y-%m-%d"))
                cols[3].write(ti.start.strftime("%H:%M"))
                cols[4].write(ti.status.name)
        else:
            st.caption("Nothing completed yet.")

# =======================================================

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# -------------------------------------------------------
# Sidebar: owner, pet list, and add-pet form
# -------------------------------------------------------
with st.sidebar:
    st.header("🐾 PawPal+")

    owner.name = st.text_input("Owner", value=owner.name or "Owner")

    if st.button("📅 Overall schedule", use_container_width=True):
        st.session_state.view = 'schedule'
        st.rerun()

    st.divider()
    st.subheader("Pets")

    if owner.pets:
        for pet_id, pet in owner.pets.items():
            if st.button(f"{pet.name} ({pet.species})", key=f"pet_{pet_id}", use_container_width=True):
                st.session_state.view = 'pet'
                st.session_state.selected_pet_id = pet_id
                st.session_state.editing_pet = False
                st.session_state.adding_task = False
                st.session_state.editing_task_id = None
    else:
        st.caption("No pets yet. Add one below.")

    st.divider()

    with st.form("add_pet", clear_on_submit=True):
        st.subheader("Add a pet")
        new_name = st.text_input("Name", value="Mochi")
        new_species = st.text_input("Species", value="dog")
        new_breed = st.text_input("Breed", value="")
        new_dob = st.date_input("Date of birth", value=dt.date(2023, 1, 1))

        if st.form_submit_button("Add pet", use_container_width=True):
            pet = Pet(
                new_name,
                new_species,
                new_breed or None,
                dt.datetime.combine(new_dob, dt.time()),
            )
            pet_id = owner.addPet(pet)
            st.session_state.view = 'pet'
            st.session_state.selected_pet_id = pet_id
            st.rerun()

# -------------------------------------------------------
# Selected pet's details and tasks
# -------------------------------------------------------
selected_id = st.session_state.selected_pet_id

if st.session_state.view == 'schedule':
    render_schedule_view()
elif selected_id is None or selected_id not in owner.pets:
    st.title("🐾 PawPal+")
    st.info("Select a pet from the sidebar, or add a new one to get started.")
else:
    pet = owner.pets[selected_id]

    st.title(f"{pet.name}")

    age_days = (dt.date.today() - pet.dob.date()).days
    if age_days >= 365:
        age = f"{age_days // 365} yr"
    elif age_days > 7 * 12:
        age = f"{round(age_days / 30.436)} mo"
    else:
        age = f"{age_days // 7} wk"

    breed = f" ({pet.breed})" if pet.breed else ""
    st.caption(f"{pet.species}{breed}  ·  {age}  ·  {'Active' if pet.active else 'Inactive'}")

    # ---- Edit pet attributes (shown only after clicking Edit) ----
    if not st.session_state.editing_pet:
        if st.button("✏️ Edit pet info"):
            st.session_state.editing_pet = True
            st.rerun()
    else:
        with st.form(f"edit_pet_{selected_id}"):
            st.subheader("Edit pet info")
            edit_name = st.text_input("Name", value=pet.name)
            edit_species = st.text_input("Species", value=pet.species)
            edit_breed = st.text_input("Breed", value=pet.breed or "")
            edit_dob = st.date_input("Date of birth", value=pet.dob.date())
            edit_active = st.checkbox("Active", value=pet.active)

            save, delete, cancel = st.columns(3)
            if save.form_submit_button("Save changes", use_container_width=True):
                pet.name = edit_name
                pet.species = edit_species
                pet.breed = edit_breed or None
                pet.dob = dt.datetime.combine(edit_dob, dt.time())
                pet.active = edit_active
                st.session_state.editing_pet = False
                st.rerun()
            if cancel.form_submit_button("Cancel", use_container_width=True):
                st.session_state.editing_pet = False
                st.rerun()
            if delete.form_submit_button("🗑️ Delete", use_container_width=True):
                app.deletePet(selected_id)
                st.session_state.view = 'schedule'
                st.session_state.selected_pet_id = None
                st.session_state.editing_pet = False
                st.rerun()

    st.divider()
    st.subheader("Current tasks")

    if pet.tasks:
        widths = [2, 1, 1, 1, 1, 1, 1]
        head = st.columns(widths)
        for col, label in zip(head, ["Task", "Priority", "Start", "Duration", "Interval"]):
            col.markdown(f"**{label}**")

        for task_id, task in list(pet.tasks.items()):
            cols = st.columns(widths)
            cols[0].write(task.name)
            cols[1].write(task.priority.name)
            cols[2].write(task.ideal_start_time.time().strftime("%H:%M"))
            cols[3].write(format_interval(task.duration))
            cols[4].write(format_interval(task.interval))
            if cols[5].button("✏️", key=f"edit_task_{task_id}"):
                st.session_state.editing_task_id = task_id
                st.session_state.adding_task = False
                seed_task_state("edit_task", task)
                st.rerun()
            if cols[6].button("🗑️", key=f"del_task_{task_id}"):
                if st.session_state.editing_task_id == task_id:
                    st.session_state.editing_task_id = None
                app.delete_task(selected_id, task_id)
                st.rerun()
    else:
        st.info(f"{pet.name} has no tasks yet.")

    # ---- Edit an existing task (shown when a row's edit button is clicked) ----
    edit_tid = st.session_state.editing_task_id
    if edit_tid is not None and edit_tid in pet.tasks:
        st.divider()
        st.subheader("Edit task")
        render_task_fields("edit_task")
        save, cancel = st.columns(2)
        if save.button("Save task", use_container_width=True, key="save_edit_task"):
            updated = build_task("edit_task")
            existing = pet.tasks[edit_tid]
            for attr in ("name", "desc", "ideal_start_time", "duration",
                         "interval", "type", "priority", "flexibility"):
                setattr(existing, attr, getattr(updated, attr))
            existing.active = st.session_state[f"edit_task_active"]
            st.session_state.editing_task_id = None
            st.rerun()
        if cancel.button("Cancel", use_container_width=True, key="cancel_edit_task"):
            st.session_state.editing_task_id = None
            st.rerun()

    # ---- Add a task (shown only after clicking Add task) ----
    if not st.session_state.adding_task:
        if st.button("➕ Add task"):
            st.session_state.adding_task = True
            st.session_state.editing_task_id = None
            seed_task_state("add_task")
            st.rerun()
    else:
        st.divider()
        st.subheader("Add a task")
        render_task_fields("add_task")
        save, cancel = st.columns(2)
        if save.button("Add task", use_container_width=True, key="save_add_task"):
            app.addTask(selected_id, build_task("add_task"))
            st.session_state.adding_task = False
            st.rerun()
        if cancel.button("Cancel", use_container_width=True, key="cancel_add_task"):
            st.session_state.adding_task = False
            st.rerun()
