---
name: parallel-dispatch
description: Decompose work into units that can genuinely run at once, dispatch one agent per unit in a single message, and recover when one comes back short. Triggers include "do these in parallel", "fan this out", "run them concurrently", "split this up", "one agent per file". Do NOT use when the units share files, when interfaces are still moving, or for a single task - a fan-out of one is a dispatch with extra steps.
---

# Parallel dispatch

Read this before dispatching more than one agent. It replaces a rule that said
*never two implementers at once* with a check that says *these two, because their
file sets are disjoint and their interfaces are frozen*.

## Why the old rule existed, and why it is not the answer

`executing-plans` banned concurrent implementers, and the reason it gave was
sound: "plan tasks touch overlapping files far more often than they appear to."
Concurrent writers in one checkout corrupt each other, and nothing notices
until review.

But a ban is a mechanism that fails in the expensive direction. A twelve-task
plan of genuinely independent work ran twelve rounds instead of three, every
time, forever — and the ban was a *rule*, which means it also had to be
remembered. The layer's own constitution says to prefer a mechanism.

So: `tools/parallel_groups.py` computes the answer from the plan, and the plan is
the artifact under test.

## The three preconditions, checked in order

**1. Declared file sets.** Every task states every path it writes. A task with no
`Files:` line is not schedulable — not warned about, not guessed at. Guessing the
file set from prose reintroduces exactly the overlap the ban was protecting
against, while looking like a check.

**2. Frozen interfaces.** Isolation solves two writers in one checkout; it does
nothing for two writers agreeing on a function signature that does not exist yet.
If task 4 consumes what task 2 produces, task 4 declares `Depends on: 2` and the
scheduler puts them in different rounds. **An interface still under discussion is
not a dependency — it is a reason not to be executing yet.**

**3. Shared surfaces run alone.** Migrations, lockfiles, CI configuration,
release config. The conflict is in the resource, not the path, so disjointness
does not help: a pair of agents each adding one dependency both rewrite the
whole lockfile. `parallel_groups.py` gives these a round to themselves.

## Running it

```bash
python tools/parallel_groups.py docs/plans/2026-08-07-thing.md
```

Exit 0 means schedulable. Anything else names the task and what it is missing —
fix the plan, not the scheduler. Output is rounds:

    round 1   x3      task(s) 1, 2, 5
    round 2   SERIAL  task(s) 3
        -> shared surface: package-lock.json

**Dispatch every task in a round in one message.** Separate messages run
sequentially and the whole computation was for nothing.

**Verify the round before starting the next.** Not each task — the round. A
round's tasks are independent of each other by construction, but the next round
depends on all of them, and an agent reporting `DONE` is a claim rather than
evidence. Read the diff.

## Decomposing a prompt that is not yet a plan

"Fix these five failing tests" and "map this codebase" are already fan-outs; they
just have no plan file. The same three preconditions apply, and the unit
definition comes from elsewhere:

| Work | Unit | Disjointness comes from |
|---|---|---|
| unfamiliar repo | subsystem | `tools/recon.py --units`, disjoint by construction |
| several unrelated failures | one failure | different subsystems, no shared cause |
| a large diff to review | one angle | read-only; overlap is harmless |
| several sources to read | one source | read-only, and each writes its own digest |
| plan tasks | one task | `tools/parallel_groups.py` |

**Read-only fan-outs need no disjointness check at all.** Two reviewers reading
the same file is duplicated effort, not corruption — so the ceiling on those is
cost, not safety. Everything that writes needs the check.

**One-per-unit, never one-per-agent-you-can-think-of.** Four `diff-reviewer`
dispatches over four *angles* is a decomposition. Four over the same angle is
four opinions and no more coverage.

## When one comes back short

Do not improvise. The ladder is computed:

```bash
python tools/loop.py --agent-status BLOCKED --attempt 1
```

| Status | First rung | Then | Then |
|---|---|---|---|
| `DONE` | accept — after reading the diff | | |
| `DONE_WITH_CONCERNS` | accept, record the concern verbatim | | |
| `NEEDS_CONTEXT` | supply the one named fact, re-dispatch (×2) | serialize | diagnose |
| `BLOCKED` | escalate the model once | serialize | diagnose |
| died / returned nothing | escalate once | serialize | diagnose |

Two rungs carry the weight:

- **`escalate`, never `retry`.** Re-dispatching `BLOCKED` unchanged on the same
  model is the same brief, the same weights, the same answer. Either the brief
  changes or the model does.
- **`serialize` terminates the ladder.** Pull the task back into the main
  context, where you can see what the agent could not. It is offered exactly
  once; after that the failure belongs to `systematic-debugging`.

## Constraints

- **A worktree per writing agent.** `task-implementer` carries
  `isolation: worktree`; it costs ~200–500ms and disk, and is removed
  automatically when nothing changed. Two writers in one checkout is the
  corruption the whole check exists to prevent.
- **Never let an agent commit, push or merge.** The dispatcher owns integration,
  and a round of agents each committing produces a history nobody can read.
- **Hand over paths, never pasted text.** Everything pasted into a dispatch stays
  in your context for the rest of the session — which is the cost the fan-out was
  supposed to avoid.
- **Say what you did not dispatch.** A capped fan-out that prints nothing about
  the cap reads as complete coverage. Name the remainder.
- **A fan-out of one is not a fan-out.** Do it inline.

## Red flags

- "These tasks look independent." — run the scheduler.
- "I'll just dispatch them one at a time to be safe." — that is the old rule,
  and it costs a round per task.
- "The agent said DONE so I ticked the box." — the diff is the evidence.
- Dispatching a round while the previous round's diff is unread.
- A `NEEDS_CONTEXT` answered by pasting the whole plan into the retry.
