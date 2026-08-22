---
name: parallel-dispatch
description: Decompose work into units that can genuinely run at once, dispatch one agent per unit in a single message, and recover when one comes back short. Triggers include "do these in parallel", "fan this out", "run them concurrently", "split this up", "one agent per file". Do NOT use when the units share files, when interfaces are still moving, or for a single task - a fan-out of one is a dispatch with extra steps.
---

# Parallel dispatch

Read this before dispatching more than one agent. It replaces a rule that said
*never two implementers at once* with a check that says *these two, because their
file sets are disjoint and their interfaces are frozen*.

## Why the old rule existed, and why it is not the answer

`implementation` banned concurrent implementers, and the reason it gave was
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

## Proving a fan-out actually ran

An agent reporting `DONE` is a claim. The tree is the evidence, and the two
questions it answers are separate:

    git -C <worktree> merge-base --is-ancestor <working branch> HEAD   # right base?
    git -C <worktree> diff --stat                                      # did it write?

Check both, per worktree, before the next round. A wrong base gives a clean diff
against the wrong repository, and nothing inside that worktree looks wrong.

**Also read what a `DONE_WITH_CONCERNS` is actually saying.** The most useful
thing a fan-out has produced here was an agent that built its function, refused
to wire it because the calling file was outside its declared file set, and named
the file it would have needed. That refusal is the scope rule working, and it is
invisible in a self-report skimmed for the word `DONE`.

**Say what a run does not prove.** Two disjoint agents working is not evidence
for three, nor for an agent that must consume another's output mid-round, nor
for recovery from a real mid-round conflict. Claim the case you measured.

## Running it

```bash
python tools/parallel_groups.py docs/plans/YYYY-MM-DD-thing.md
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

**A schedulable round is dispatched by default** — see `implementation/
SKILL.md`'s own "Dispatching subagents for parallel tasks" — and each
task's worktree is created on its own named branch instead of detaching,
so its result can be pushed and turned into its own PR:

```bash
python tools/worktree.py create task6 feat/target-workflow --branch feat/target-workflow/task-6
```

Everything else about owning the worktree yourself (below) is unchanged —
the branch mode is additive, not a different creation path.

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

**One-per-unit, never one-per-agent-you-can-think-of.** Four `reviewer`
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
  once; after that the failure belongs to `debugging`.

## Constraints

- **A worktree per writing agent, and CHECK THE BASE FIRST.**
  `isolation: worktree` bases the agent's tree on the repository's **default
  branch**, not on the branch this session has checked out. Measured, not
  assumed: a probe agent dispatched from `rebuild-capability-layer` (at
  `4abf946`) landed in a worktree at `af3cdda` on a fresh branch
  `worktree-agent-<id>`.

  That is the whole explanation for the first fan-out failing. `main` was the
  initial commit at the time, so the whole round was handed a tree with none of the
  work they were asked to extend. Three returned BLOCKED; two wrote into trees
  nobody could see. Nothing reported a stale base, because from inside the
  worktree nothing is wrong -- it is a clean checkout of a real commit.

  **Re-measured since, and it is still true.** Two `implementer` agents
  dispatched from a feature branch got worktrees on the default branch instead;
  `git merge-base --is-ancestor <feature> HEAD` inside them exited **1**. Prose
  about this bug did not change the behaviour, because prose was never what set
  the base. Re-run that command in any worktree you are handed before trusting
  it — the answer is a fact about your repository, not about this one.

  Both then refused to launch with *"git could not be run to resolve it, so its
  git identity could not be verified"*. That message is a **false cause**: git
  resolves those worktrees fine from a shell — `rev-parse HEAD` and
  `rev-parse --show-toplevel` both answer correctly. So `isolation: worktree`
  currently fails twice over, and the second failure hides the first.

  **The remedy is to own the worktree instead of asking for one.** Create it
  yourself, naming the base out loud, and dispatch an agent that does not force
  its own isolation:

  ```bash
  python tools/worktree.py create task6 feat/target-workflow   # prints path + base SHA
  # dispatch a NON-worktree agent, pointing it at that absolute path
  git -C .worktrees/task6 merge-base --is-ancestor feat/target-workflow HEAD
  python tools/worktree.py remove task6
  ```

  `worktree.py` takes `base` as a required positional with no default, because
  the convenient default *is* the bug. It returns the resolved base SHA so the
  caller can assert on it rather than trust that the call exiting 0 meant the
  right thing happened — which is precisely what every agent in the failed
  fan-out did.

  This superseded the previous advice here, which was "do not use worktrees on
  an unmerged branch: dispatch serially in-tree, or merge first". That was a
  real remedy and it cost the whole mechanism; merging unfinished work to get
  isolation is backwards.

  Two writers in one checkout is the corruption the whole check exists to
  prevent, so the isolation is not optional — only its provenance changed.
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
