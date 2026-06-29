# PawPal+ Project Reflection

## 1. System Design

Core actions: Add Pet, add Need, generate Schedule, see Schedule

**a. Initial design**

- Briefly describe your initial UML design.
     - `Owner` has `Pet`s. `Pet` has `Task`s. Scheduler populates self with `TaskInstance`s
- What classes did you include, and what responsibilities did you assign to each?
    - Task, Pet, Owner, Scheduler. 

**b. Design changes**

- Did your design change during implementation?
    - Yes
- If yes, describe at least one change and why you made it.
    - Added a `TaskInstance` class. The assignment structure lists a single `Task` that holds both its definition and its completion status, but because tasks recur daily there was no place to record completion per occurrence — one `Task` ("give medication every 6 hours") can be done once and missed later. So I split the model: `Task` is the recurring definition (name, ideal start time, flexibility, duration, frequency, type, priority), and `TaskInstance` is a single day's occurrence (scheduled time, status, notes). Completion status lives on the instance. `status` is set by the user and `notes` can record *why* something was skipped or missed. 

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
