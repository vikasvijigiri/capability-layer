# Workflow policy

This is the durable SDLC contract. **One engine implements it**: `tools/resume.py`
derives the state from git and `tools/loop.py` decides the recovery rung. A second
implementation in JavaScript — `.claude/workflows/feature-delivery.js` plus a
251-line `tools/run_workflow.mjs` — was deleted on 2026-08-07; it kept its own
budget table in a different vocabulary, held run state in memory so a crash lost
it, and could not be invoked as `/feature-delivery` because it never matched the
dynamic-workflow contract. See `decisions/2026-08-07-one-workflow-engine.md`.

The policy is harness-agnostic: Claude Code, Codex, Gemini, and VS Code agents
must use the same states, artifacts, evidence, and approval boundaries. Both
tools are plain scripts, so any harness can shell out to them.

## Product lifecycle

**The numbers are labels, not a sequence.** Stage 2 is conditional and most work
skips it; a session that reads this table top-to-bottom and runs every row has
misread it. The `Runs when` column is the whole entry rule — see **Entry** below,
which is the only place it is stated.

| # | Stage | Owner | Runs when | Output |
|---|---|---|---|---|
| 1 | Frame and plan | `writing-plans` | work is named, at any scope | `TASK.md`'s six fields, then executable steps, ownership, checks, risks, rollback |
| 2 | Design | `brainstormer` | **only if the approach is open** — dispatched by stage 1, not entered beside it | decision/spec when ambiguity is material |
| — | Gate 1 | user | a plan exists | plan approval only |
| 3 | Execute | `executing-plans` | Gate 1 passed, or the change was too small to plan | scoped implementation in an isolated worktree |
| 4 | Validate | `verifying-work` | completion is claimed, in any wording | acceptance and test evidence |
| 5 | Sweep | `no-slop` | before a diff is reviewed | prose, wiring, safety, and quality findings |
| 6 | Review | `code-review` | a diff is about to be delivered | automated diff verdict with file/line evidence |
| 7 | Deliver | `delivering` | review signed off | branch/PR/merge-queue handoff and conflict evidence |
| 8 | Release | `releasing` | **only if there is a deploy target** | release candidate, shipment gate, observation, rollback |
| 9 | Record | `knowledge-manager` | always, to close the unit | durable log, handoff, issues, memory, decisions |

**The stages renumbered on 2026-08-09**, when framing and planning merged into
one owner and stage 1 absorbed the old stage 1. Ten became nine. Any document
still saying "stage 3 is the plan" predates that and is wrong; the table here is
the only authority, and `tools/test_process_router.py` fails on a gap or a
repeat in the left column.

There are exactly two human gates: approval of the plan after stage 1, and
approval of the release candidate after stage 8 readiness. No review, delivery,
merge, or mid-run diagnostic may ask for another approval. A host may still
require its own platform permission prompt for an irreversible tool operation;
that is execution control, not a lifecycle gate.

## Entry

**This section owns the entry rule. Nowhere else states it.** It was written in
seven places until 2026-08-08 and the suite needed a special-case
`FORBIDDEN_SUCCESSOR` check to stop the copies drifting apart, which is what a
boundary looks like when it is being restated instead of owned.

**On 2026-08-09 the boundary was removed rather than guarded.** Framing and
planning are one skill now, so the question the old rule asked — brief or design
— is no longer answered at the door. It is answered inside stage 1, against the
six fields, where the evidence for it actually exists.

| The request | Goes to | Because |
|---|---|---|
| names work, at any scope | 1 `writing-plans` | it frames, fetches what is missing, then plans |
| repository nobody has read | `repo-recon` first | see **The entry boundary** below |
| a current failure | `systematic-debugging` | a cause is not a plan |

One entry, one owner. The old rule's real content did not disappear — it moved
into stage 1's Stage B table, which decides per blank field rather than per
request:

- **Goal or Outputs blank because the approach is undecided** → stage 1
  dispatches 2 `brainstormer` *before* writing `TASK.md`, because a finished
  brief commits to one solution shape and that anchor is what stage 2 exists to
  prevent.
- a constraint turning on outside evidence → `research`;
- a user-facing surface with no contract → `designer`;
- an unread repository → `repo-recon`;
- a blocking failure of unknown cause → `systematic-debugging`.

Each returns to stage 1. **None of them is a handoff**, and that is the
difference from the old chain: a dispatch resumes where it left off, so there is
no seam for the work to fall through. The seam was real — an un-handed-off brief
was the chain's most common break, and nothing watched for one.

The rest of the chain is linear: 3 `executing-plans` builds, 4 `verifying-work`
validates, 5 `no-slop` sweeps, 6 `code-review` reviews, 7 `delivering`
integrates, 8 `releasing` observes, 9 `knowledge-manager` records. These are
lifecycle labels, not additional approval gates.
The recovery loop returns to `3 executing-plans` or `4 verifying-work`, then
re-enters `6 code-review` and `8 releasing` when the candidate is ready again.

## State machine and failure loop

**In code, not here.** `tools/resume.py` derives the state from git facts and
`tools/loop.py` decides the rung; their tests are the specification. This section
described 21 states and six budgets from 2026-08-06 to 2026-08-07, and a grep for
those names returned exactly one file — this one. See
`decisions/2026-08-07-derived-state-over-stored-state.md`.

    python tools/resume.py     # where this unit of work is
    python tools/loop.py       # what to do about the failure, and when to stop

State is never stored. Nothing to persist, nothing to migrate, nothing to
desync — the only exception is an attempt counter, which is not a fact about the
tree and so cannot be derived from it.

## Parallelism and integration

Parallel agents may work only on disjoint files or read-only review surfaces.
Each implementation task gets its own worktree and branch. Shared interfaces,
lockfiles, migrations, and release configuration are serialized.

**That rule is now computed, not remembered.** It said the same thing from
2026-08-06, and nothing implemented it: `executing-plans` resolved the ambiguity
by banning concurrent implementers outright, which was safe, cost a round per
task forever, and was still only a rule. Two scripts now decide:

    python tools/parallel_groups.py <plan>   # which tasks may run together
    python tools/recon.py --units            # which subsystems may be read together

`parallel_groups.py` reads each task's declared `Files:` and `Depends on:` and
prints rounds. It **refuses a plan rather than guessing**: a task with no declared
file set, or a dependency written as prose instead of a task number, is
unschedulable. Absent is never read as none — the convenient reading of a missing
dependency is a concurrent dispatch over ordered work, which is the one failure
worse than being slow. Depth is in
`.claude/skills/executing-plans/references/parallel-dispatch.md`.

A dispatch also needs a bounded ladder, because an agent fails in ways a check
does not — it can report that its own brief was incomplete, or die before
reporting at all:

    python tools/loop.py --agent-status BLOCKED --attempt 1

Rungs are supply, escalate, serialize and diagnose. `BLOCKED` escalates the model
once and is never re-dispatched unchanged — same brief, same weights, same
answer. The serialize rung pulls the task back into the main context and is
offered exactly once, which is what makes the ladder terminate.

Candidate promotion is evidence-based: required checks, acceptance coverage,
security, scope, rollback, performance, and conflict status; tie-break by smaller
diff, fewer dependencies, stronger tests, and lower risk. Configure protected
branches, required checks, and merge queue in the hosting service; the workflow
never force-pushes or bypasses them.

## Artifacts and ownership

`TASK.md` and `docs/plans/` — `writing-plans` · `docs/specs/` — `brainstormer`
· `ISSUES.md` — `systematic-debugging` · `LOG.md`, `HANDOFF.md`,
`MEMORY.md`, and `decisions/` — `knowledge-manager` · workflow run state — the
repository workflow runner. Chat is not durable evidence.

## Cross-cutting capabilities

Use `research` for external evidence and `systematic-debugging` for any failure.
Depth that used to be its own skill now lives in `<skill>/references/` and is read
per task — the artifact review that gates a material spec or plan is
`writing-plans/references/artifact-review.md`, not a skill of its own. Maintain the
capability layer with `capability-layer-maintenance`; it may repair wiring but
never authors product strategy.

## Invariants

- No completion claim without actual evidence from the relevant tree.
- No secrets, unsafe branch operations, or unattended spend.
- No side-effecting release before Gate 2.
- No unresolved review, security, test, scope, or merge finding proceeds.
- No silent retry; every attempt and stop reason is recorded.
- Every unit ends in `knowledge-manager` recording or an explicit `BLOCKED` state.

[state:docs-stale]
The durable knowledge artifacts are behind the current workflow run. Resume
`knowledge-manager` before claiming the unit complete.
[/state:docs-stale]

[state:no-remote]
This branch has commits and no git remote, so nothing can be pushed, no pull
request can exist, and the merge-queue configuration in `.github/workflows/`
has never been exercised against the service that enforces it. `/publish`
creates the repository, pushes, opens the PR, and prints the branch-protection
settings to enable by hand. It needs an explicit yes -- publishing is
outward-facing and a repository, once public, can be indexed before it is deleted.
[/state:no-remote]

[state:layer-unreviewed]
The capability layer changed without a completed layer audit. Run the
capability-layer-maintenance audit and the no-slop layer scan before delivery.
[/state:layer-unreviewed]

[state:entry-unframed]
This prompt names work with a done-state, and the **Entry** table above routes
named work at any scope to stage 1 `writing-plans`. Frame it first: six fields,
every inferred one marked, no dialogue -- Gate 1 is the plan, not the brief. Then
continue through its Stage B and Stage C in the same turn. If the work turns out
too small to plan, say "too small to plan" and just do it.
[/state:entry-unframed]

[state:entry-open]
This prompt names work whose approach is **not settled**. It still enters at
stage 1 `writing-plans` -- there is one door as of 2026-08-09 -- but the first
thing that skill does with an undecided approach is dispatch 2 `brainstormer`,
*before* `TASK.md` is written. Order matters and is the whole point: a finished
brief commits Goal and Outputs to one solution shape, and that anchor is what
stage 2 exists to prevent. `brainstormer` returns here; it is a dispatch, not a
handoff.
[/state:entry-open]

## The entry boundary

The chain assumes a repository somebody has read. When it is dropped into one
nobody has, that assumption is the first thing to fail, and it fails quietly:
stage 1 frames a *request*, so a brief written against an unread codebase looks
exactly like a brief written against a known one.

`repo-recon` owns that boundary. It runs before stage 1 when there is real code
and no map, and never again once a map exists at `docs/recon/`. It is not a
numbered stage — a repository this layer has been used in from the start never
enters it.

`tools/resume.py` derives the distinction, so nothing has to remember it: no plan
plus 20 or more tracked code files plus no map is `RECON`, and no plan with
anything less is `PLANNING`. Until 2026-08-07 both were `PLANNING` — measured
against this repository, 104 commits of finished work reported as
`state=PLANNING`, because every fact the engine reads is a fact about this layer's
own artifacts and a repository that never used the layer has none of them.

## Off-chain capabilities

These skills are reusable capabilities, not additional lifecycle stages:

| Capability | Owner | Use |
|---|---|---|
| Comprehend | `repo-recon` | an unread or half-finished repository, at the entry boundary |
| Research | `research` | external evidence |
| Design | `designer` | a user-facing surface with no design contract; produces `DESIGN.md` |
| Diagnose | `systematic-debugging` | root-cause and bounded recovery |
| Maintain | `capability-layer-maintenance` | layer contracts and wiring |
