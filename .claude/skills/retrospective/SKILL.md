---
name: retrospective
model: opus
description: Extracts the durable lesson from finished work - what to keep doing, what to change, and what was learned that is not obvious from the diff. Use after a unit of work completes and for "what did we learn", "how did that go", "retro", "lessons learned", "what would we do differently", "that was painful", "why did that take so long", "post mortem on the process". Prefer this over moving straight to the next task - a lesson not written down is re-learned at full price. Do NOT use for incident causation - that is root-cause-analysis.
effort: high
---

# Retrospective

About the *process*, not the defect. `root-cause-analysis` explains why something broke;
this explains why the work went the way it did.

## Steps

1. **Compare plan to actual.** Where did the work diverge from `PLAN.md`, and was the plan
   wrong or the execution? Both are useful; they have different fixes.
2. **Find the time sinks.** What consumed effort disproportionate to its value, and was
   that predictable in advance?
3. **Separate three categories** - and only one is worth recording:
   - **One-off** - will not recur. Do not record it.
   - **Recurring** - will happen again. Record it.
   - **Structural** - caused by how the system is set up. Record it and name the change.
4. **Apply the durability test** before writing anything down: would this still be true in
   three months, independent of this specific task? If not, it does not belong in
   `MEMORY.md`.
5. **Check for a promotion candidate.** If the same solution shape has now appeared
   repeatedly, route to `blueprint-promoter`.

## Output

At most a handful of durable lessons, written through `knowledge-manager` into `MEMORY.md`.
Prefer one genuinely load-bearing line over five generic ones - "add more tests" is not a
lesson, it is a slogan.

## Rules

- **Blameless.** Process failures, not people. "Nobody checked" is a missing gate.
- **A retrospective that produces no change is theatre.** If nothing should change, say
  that explicitly rather than inventing an action item.
