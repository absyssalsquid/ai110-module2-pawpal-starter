# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

These were completed during algorithmic development rather than post hoc in order to make development smoother and eliminate code rewriting.

## Challenge 1: Advanced Algorithmic Capability
Flexibility scheduling: tasks can be delayed up to a limit

**What task did you give the agent?**

Two related asks:
1. "How could the `insert` function be simplified for better readability or performance?"
2. "Write test cases for `fit_with_delay`. Consider edge cases."

**What did the agent do?**

- Proposed decomposing `insert` into single-responsibility helpers — `find_gap` (first free slot), `extract_conflicts` (evict overlaps), and `fit_with_delay` (shift a task later within its flexibility) — and explained the readability/testability/performance trade-offs.
- Wrote pytest cases in `tests/test_pawpal.py` for `fit_with_delay`, with `at()`/`sched_ti()` helpers and documented edge cases

**What did you have to verify or fix manually?**

The agent flagged a real bug: the backward scan (`while self.schedule[b_i].end > ti.start`) had no lower bound, so when a task's ideal start preceded every scheduled instance's end, `b_i` went negative and Python's wraparound indexing eventually raised `IndexError`. It captured this as an `xfail` test. I fixed it by adding a `b_i >= 0` guard to the loop condition, which made the edge case pass.


## Challenge 3: Advanced Priority Scheduling
Tasks are scheduled based on priority first

**What task did you give the agent?**

"Write test cases for `extract_conflicts`. Consider edge cases." This is the method that lets a higher-priority task push lower-priority ones out of a contested time slot

**What did the agent do?**

- Read `extract_conflicts` and `insert` to confirm the priority model (enum where a larger `.value` means lower priority: `HIGH=1 < MED=2 < LOW=3`) and how evicted instances are re-inserted in priority order.
- Wrote tests covering: a single lower-priority overlap removed, equal-priority overlap **kept** (the comparison is strict `>`, not `>=`), higher-priority overlap kept, touching boundaries not counted as overlap, multiple evictions returned in reverse schedule order (back-to-front scan), non-conflicting survivors keeping their order, and a zero-duration `ti` inside an interval.

**What did you have to verify or fix manually?**

Confirmed the intended semantics the tests assert — chiefly that equal-priority conflicts are deliberately left alone (so two same-priority tasks don't evict each other and instead fall through to the delay path), and that `extract_conflicts` mutates `self.schedule` in place while returning the evicted instances in reverse order for `insert` to re-place.

---
