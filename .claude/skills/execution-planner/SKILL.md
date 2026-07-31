---
name: execution-planner
model: opus
description: Turns an approved brief into PLAN.md - ordered steps, dependencies, risks and acceptance criteria - so the order of work is decided once rather than improvised per step. Use for "plan this out", "what order should we do this in", "break this down", "write the plan", "where do we start", "what needs to happen first", "how should we approach this", "give me the steps". Prefer this over starting at step one and discovering the ordering later - rework from a missed dependency costs more than the planning did. Do NOT use for single-step work, or before requirements exist - that is requirements-analyst.
effort: high
---

# Execution Planner

Produces the content of `PLAN.md`. `knowledge-manager` owns its *format*; this skill owns
what goes in it. Nothing else produces a plan.

## Steps

1. **Read the brief.** No plan without an approved goal - if there is none, stop and route
   to `task-intake` or `requirements-analyst`.
2. **Write the Objective** as a single done-condition, not a description of activity.
3. **Decompose into steps that each end in something checkable.** A step whose completion
   cannot be observed is a wish, not a step.
4. **Declare dependencies explicitly**, including implicit ones - a contract that must be
   frozen before two pieces can proceed in parallel, a migration that must land before
   code reading the new column.
5. **Mark what can run in parallel.** Disjoint files plus a frozen contract makes a
   subagent candidate; shared files do not. Route non-obvious splits through
   `work-decomposition`.
6. **List risks with a trigger and a response**, not adjectives. "The API may be slow" is
   useless; "if p95 exceeds 400ms at step 4, fall back to the cached path" is a plan.
7. **Acceptance criteria per step**, drawn from the brief. A step mapping to no criterion
   may not belong in scope at all.

## Output

`PLAN.md` in the canonical format (Objective / Execution Plan / Dependencies / Risks /
Acceptance Criteria), written via `knowledge-manager` so the format stays consistent.

## Rules

- **Order by dependency, not by comfort.** The tempting order is easiest-first; the
  correct order is whatever unblocks the most downstream work.
- **Put the risky step early**, where changing course is still cheap. A plan deferring its
  only real unknown to the last step is a plan that will be rewritten.
- Route to `approval-brief` before executing anything irreversible.
