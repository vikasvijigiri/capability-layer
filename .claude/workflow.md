# Workflow policy

This is the durable SDLC contract. The executable state machine is
`.claude/workflows/feature-delivery.js`; its runtime is `tools/run_workflow.mjs`.
The policy is harness-agnostic: Claude Code, Codex, Gemini, and VS Code agents
must use the same states, artifacts, evidence, and approval boundaries.

## Product lifecycle

| # | Stage | Owner | Output |
|---|---|---|---|
| 1 | Frame | `task-brief` | bounded goal, constraints, done-check, out-of-scope |
| 2 | Design | `brainstormer` | decision/spec when ambiguity is material |
| 3 | Plan | `writing-plans` | executable steps, ownership, checks, risks, rollback |
| — | Gate 1 | user | plan approval only |
| 4 | Execute | `executing-plans` | scoped implementation in an isolated worktree |
| 5 | Validate | `verifying-work` | acceptance and test evidence |
| 6 | Sweep | `no-slop` | prose, wiring, safety, and quality findings |
| 7 | Review | `code-review` | automated diff verdict with file/line evidence |
| 8 | Deliver | `delivering` | branch/PR/merge-queue handoff and conflict evidence |
| 9 | Release | `releasing` | release candidate, shipment gate, observation, rollback |
| 10 | Record | `knowledge-manager` | durable log, handoff, issues, memory, decisions |

There are exactly two human gates: approval of the plan after stage 3, and
approval of the release candidate after stage 9 readiness. No review, delivery,
merge, or mid-run diagnostic may ask for another approval. A host may still
require its own platform permission prompt for an irreversible tool operation;
that is execution control, not a lifecycle gate.

`task-brief` branches from an idea to `brainstormer` when the direction is
unknown, or proceeds to stage 3 when scope is already settled. 1 `task-brief` frames, 2 `brainstormer` designs, 3 `writing-plans` plans, 4 `executing-plans` builds, 5 `verifying-work` validates, 6 `no-slop` sweeps, 7 `code-review` reviews, 8 `delivering` integrates, 9 `releasing` observes, and 10 `knowledge-manager` records.
These numbers are lifecycle labels, not additional approval gates.
The recovery loop returns to `4 executing-plans` or `5 verifying-work`, then
re-enters `7 code-review` and `9 releasing` when the candidate is ready again.
The contract also rechecks 1 `task-brief` and 2 `brainstormer` at the entry
boundary.

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
lockfiles, migrations, and release configuration are serialized. Candidate
promotion is evidence-based: required checks, acceptance coverage, security,
scope, rollback, performance, and conflict status; tie-break by smaller diff,
fewer dependencies, stronger tests, and lower risk. Configure protected branches,
required checks, and merge queue in the hosting service; the workflow never
force-pushes or bypasses them.

## Artifacts and ownership

`TASK.md` — `task-brief` · `docs/specs/` — `brainstormer` · `docs/plans/` —
`writing-plans` · `ISSUES.md` — `systematic-debugging` · `LOG.md`, `HANDOFF.md`,
`MEMORY.md`, and `decisions/` — `knowledge-manager` · workflow run state — the
repository workflow runner. Chat is not durable evidence.

## Cross-cutting capabilities

Use `research` for external evidence, `systematic-debugging` for any failure,
`security-review` for trust boundaries, `artifact-review` for material specs or
plans, `designer` for user-facing design, `test-driven-development` for new
behavior, `supply-chain-audit` for dependencies/CI, `performance-engineering`
for measurable resource risk, `observability-sre` for production signals, and
`accessibility-audit` for inclusive interaction evidence. Maintain the
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

[state:layer-unreviewed]
The capability layer changed without a completed layer audit. Run the
capability-layer-maintenance audit and the no-slop layer scan before delivery.
[/state:layer-unreviewed]

## Off-chain capabilities

These skills are reusable capabilities, not additional lifecycle stages:

| Capability | Owner | Use |
|---|---|---|
| Research | `research` | external evidence |
| Diagnose | `systematic-debugging` | root-cause and bounded recovery |
| Maintain | `capability-layer-maintenance` | layer contracts and wiring |
| Isolation | `using-git-worktrees` | worktree and branch safety |
| Security | `security-review` | trust boundaries and sensitive changes |
| Artifact review | `artifact-review` | independent spec/plan review |
| Design | `designer` | user-facing design and visual QA |
| Test first | `test-driven-development` | executable behavior proof |
| Supply chain | `supply-chain-audit` | dependency, CI, and provenance review |
| Performance | `performance-engineering` | measurable latency and resource risk |
| Operations | `observability-sre` | production signals and runbooks |
| Accessibility | `accessibility-audit` | inclusive interaction evidence |
