# Workflow policy

This is the durable SDLC contract. **One engine implements it**: `tools/resume.py`
derives the state from git and `tools/loop.py` decides the recovery rung. A second
implementation in JavaScript — `.claude/workflows/feature-delivery.js` plus a
251-line `tools/run_workflow.mjs` — was deleted on 2026-08-07; it kept its own
budget table in a different vocabulary, held run state in memory so a crash lost
it, and could not be invoked as `/feature-delivery` because it never matched the
dynamic-workflow contract. See `decisions/2026-08-07-one-workflow-engine.md`.

The policy is host-neutral at the artifact and safety-semantics level. Runtime
availability is not inferred: `.claude/portability/capabilities.json` defines
the capabilities each stage requires, and `.claude/adapters/` records whether a
host is native, bridge-required, or must refuse. Claude Code is the checked
native configuration. Non-Claude hosts must invoke canonical checks through
their lifecycle API and may not claim bridge-required safety controls until the
named conformance command has passed.

## Product lifecycle

**The numbers are labels, not a sequence.** Stage 2 is conditional and most work
skips it; a session that reads this table top-to-bottom and runs every row has
misread it. The `Runs when` column is the whole entry rule — see **Entry** below,
which is the only place it is stated.

| # | Stage | Owner | Runs when | Output |
|---|---|---|---|---|
| 1 | Frame and plan | `task-analysis` | work is named, at any scope | `TASK.md`'s six fields, then executable steps, ownership, checks, risks, rollback |
| 2 | Design | `architecture` | **only if the approach is open** — dispatched by stage 1, not entered beside it | decision/spec when ambiguity is material |
| — | Gate 1 | user | a plan exists | plan approval only |
| 3 | Execute | `implementation` | Gate 1 passed, or the change was too small to plan | scoped implementation in an isolated worktree |
| 4 | Validate | `testing` | completion is claimed, in any wording | acceptance and test evidence |
| 5 | Sweep | `refactoring` | before a diff is reviewed | prose, wiring, safety, and quality findings |
| 6 | Review | `code-review` | a diff is about to be delivered | automated diff verdict with file/line evidence |
| 7 | Deliver | `release-git` | review signed off | branch/PR/merge-queue handoff and conflict evidence |
| 8 | Release | `release-git` | **only if there is a deploy target** | release candidate, shipment gate, observation, rollback |
| 9 | Record | `documentation` | always, to close the unit | durable log, handoff, issues, memory, decisions |

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

### The small-work path — take it when it applies

The nine stages cost the same for a two-file change as for a twelve-task plan,
and that is the single biggest source of overhead in this layer. When
`tools/scope.py` says `small` **and** the work is not a control, shared or
sensitive surface:

    frame it in one line -> do it -> `--scoped` checks -> record one LOG line

No plan, no Gate 1, no sweep, no separate review pass — read your own diff
before you stop. Say **"small path"** out loud so the choice is visible and
reversible; anything that turns out `major` mid-flight re-enters at stage 1.

This is a narrowing of the stage table below, not an exception to it: the
invariants at the foot of this file still hold, and nothing here waives the two
gates or the delivery approval.


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
| names work, at any scope | 1 `task-analysis` | it frames, fetches what is missing, then plans |
| repository nobody has read | `repository-navigation` first | see **The entry boundary** below |
| a current failure | `debugging` | a cause is not a plan |

One entry, one owner. The old rule's real content did not disappear — it moved
into stage 1's Stage B table, which decides per blank field rather than per
request:

- **Goal or Outputs blank because the approach is undecided** → stage 1
  dispatches 2 `architecture` *before* writing `TASK.md`, because a finished
  brief commits to one solution shape and that anchor is what stage 2 exists to
  prevent.
- a constraint turning on outside evidence → `research`;
- a user-facing surface with no contract → `architecture`;
- an unread repository → `repository-navigation`;
- a blocking failure of unknown cause → `debugging`.

Each returns to stage 1. **None of them is a handoff**, and that is the
difference from the old chain: a dispatch resumes where it left off, so there is
no seam for the work to fall through. The seam was real — an un-handed-off brief
was the chain's most common break, and nothing watched for one.

The rest of the chain is linear: 3 `implementation` builds, 4 `testing`
validates, 5 `refactoring` sweeps, 6 `code-review` reviews, 7 `release-git`
integrates, 8 `release-git` observes, 9 `documentation` records. These are
lifecycle labels, not additional approval gates.
The recovery loop returns to `3 implementation` or `4 testing`, then
re-enters `6 code-review` and `8 release-git` when the candidate is ready again.

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

The host's adapter is the dispatch surface. `.claude/workflows/` holds tested,
narrow-purpose scripts (e.g. `no-slop-sweep.js`) invoked as bounded fan-outs,
not a general workflow engine; scheduling remains in the tested repository
tools below. A host without verified delegation serializes the work or refuses a
dependent required action; it never pretends an unverified fan-out is isolated.

Parallel agents may work only on disjoint files or read-only review surfaces.
Each implementation task gets its own worktree and branch. Shared interfaces,
lockfiles, migrations, and release configuration are serialized.

**As of 2026-08-21, "and branch" is the default, not an aspiration.** Any
round `parallel_groups.py` reports with concurrency > 1 dispatches
concurrently without a user asking for it by name; each task's worktree is
created on its own named branch (`tools/worktree.py`'s additive `--branch`
mode), pushed and opened as its own PR automatically once its own
verification passes. The merge step still asks — every time, live, never a
standing pre-authorization — but batched into one `AskUserQuestion` per round
covering every PR, instead of one per PR. See `release-git/SKILL.md`'s
"Exception: a parallel round's task branches" and "Exception: a parallel
round's batched merge"; `decisions/2026-08-21-branch-per-parallel-task.md`
records why. A fully-serial plan, or a round of concurrency 1, is unaffected.

**That rule is now computed, not remembered.** It said the same thing from
2026-08-06, and nothing implemented it: `implementation` resolved the ambiguity
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
`.claude/skills/implementation/references/parallel-dispatch.md`.

**The worktree's base is named explicitly, never defaulted.** `isolation:
worktree` bases an agent's tree on the repository's *default branch*, not the
branch the session is on. Measured, more than once: a fan-out dispatched from
a feature branch landed on the default branch instead. So the dispatcher creates
the worktree itself:

    python tools/worktree.py create <name> <base>   # base is a required positional

`base` has no default because the default is the bug. `create()` returns the
resolved SHA so the caller can assert `git merge-base --is-ancestor` rather than
trust that the call exiting 0 meant the right thing happened — which is exactly
what every agent in the first, failed fan-out did.

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

## How much the pipeline may trust automation with it — the risk tier

Separate from `small`/`major`, and answering a different question. That one asks
how much of the repository a change should be checked against; this asks how far
the work may travel before a person looks at it.

    python tools/scope.py --plan <plan>     # 0 low · 1 medium · 2 high

Assigned at **planning time**, from the plan's own `- Create:` / `- Modify:`
lines — before any diff exists, which is the point: the tier has to be available
to decide what the rest of the run does. Same veto discipline as the scope
verdict, so it stays auditable:

| Forced by | Tier |
|---|---|
| a shared surface — migration, lockfile, CI config | `high` |
| a control surface — hooks, agents, `workflow.md`, `settings.json` | `high` |
| a sensitive surface — auth, credentials, the installer, packaging | `high` |
| volume, or spread across containers | `medium` |
| nothing | `low` |

**`undetermined` is `high`.** A plan that cannot be classified is not a low-risk
plan, and this is the last place in the chain where guessing is cheap.

`**Risk:**` is a required section of every plan — `tools/analyze.py` refuses a
plan without it, so an untiered plan cannot reach Gate 1.

### What the tier does *not* do

**It never skips Gate 2.** A low-risk shipment still asks. Auto-approve-on-low
was considered and refused: *never push, merge, publish or deploy without
explicit user approval* is the one rule in this layer with no exceptions, and a
tier computed by the same system that wants to ship is not the thing that should
be allowed to waive it. The tier decides what Gate 2 is **shown**, not whether it
is **asked**.

## How much of the repository a change is checked against

`small` and `major` decide the breadth of the tier, the sweep and the review.
Judged, the answer under deadline pressure is always `small`, so it is computed:

    python tools/scope.py            # 0 small · 1 major · 2 undetermined

A **veto list**, not a score: any one of `shared-surface`, `control-surface`,
`volume`, `spread` or `unmapped` forces `major`, and the verdict names every
clause that fired. A score would let two cheap signals outvote one expensive one
and turn an auditable decision into arithmetic nobody can check.

| Consumer | `small` | `major` |
|---|---|---|
| `run_checks.py --scoped` | the suites `test_map` maps the changed paths to | refuses, exit 2 — run the full tier |
| `refactoring --scope change` | sweeps only the changed files | `--scope repo`, the stage-5 cadence |
| `code-review` | the changed files and their direct callers | the whole branch diff |

Three rules keep "cheaper" from becoming "unmeasured", and they are the whole
safety argument:

- A scoped run prints **`PARTIAL PASS`, never `PASS`**, and names every suite it
  skipped.
- It **never moves `refs/uaios/green/<slug>`** — that ref means the full tier
  passed, and `run_checks.py` contains no ref write at all.
- An **unmapped** changed path escalates to the full tier rather than running
  nothing, so the map's gaps fail safe.

`undetermined` is read as `major` everywhere. Article V: a clause that could not
be evaluated is not permission to check less. The `test_map` itself is a coverage
*claim* — its shape is asserted, its judgement is not, and a wrongly-mapped path
makes a change fast and under-checked with no symptom.

## Safety rails added 2026-08-11

Four mechanisms, each with a tool and a suite behind it rather than a paragraph:

| | Command | What it refuses, or reports |
|---|---|---|
| **Kill switch** | `python tools/halt.py --halt "<reason>"` | While halted, `pre-tool/01-halt-guard.py` DENIES every tool that changes state or spawns work. Reads stay allowed on purpose — a halt you cannot investigate is a lockout, not a stop. `--resume` lifts it |
| **Agent file scope** | declared per agent as `allowed-paths:` | `pre-edit/02-agent-scope-guard.py` denies a write outside a dispatched agent's declared files, and an unscoped write with it. **Only when the host sets `UAIOS_AGENT_NAME`, and Claude Code does not** — see below |
| **Licence and SBOM** | `python tools/deps.py [--sbom]` | A denied licence exits 1; one that could not be read exits 2. `0` ok, and undetermined is never ok |
| **Release candidate** | `python tools/release_candidate.py --plan <plan>` | The report Gate 2 reads: wheel, rehearsal, licence, SBOM, risk tier, changed paths, and a **rollback that was executed** in a scratch repo |
| **Budget** | `python tools/budget.py` | Turns and elapsed against a ceiling, from the ledger. Reports; never halts — that is the kill switch's job |
| **Security gate** | `python tools/security_gate.py --base <ref>` | Five clauses, each a fact about the artefact: a security control that lost an entry, a secret anywhere in the branch, a sensitive path no suite maps, an agent that may write with no declared scope, a moved dependency tree `deps.py` rejects. Exit `1` fired, `2` unevaluated. Added 2026-08-11 |

**`.claude/policies/` is the same instruments cut by gate purpose** — one thin
index file each (`.claude/policies/budgets.md`, `.claude/policies/escalation.md`,
`.claude/policies/permissions.md`, `.claude/policies/security.md`), every file a
pointer to the enforcing code, not a second copy of it. Read a policy file to
see which tools serve one gate; read this table to see what each tool refuses.

**Agent file scope is dormant on this host, and that is the honest word for
it.** The guard reads `UAIOS_AGENT_NAME` to know which agent is writing, and
**nothing sets it** — a repository-wide grep finds the name only in the guard
and its own fixtures. Claude Code spawns subagents itself and has no hook that
runs inside one, so no dispatcher in this layer can set it; on a real dispatch
the guard runs and is silent. What *is* enforced on this host is each agent's
`tools:` allowlist, by the harness. The guard stays because a host that can set
the variable gets the file-glob half for free, and `tools/test_agent_standards.py`
fails if this paragraph stops naming the precondition — a claim that outlives its
wiring is the failure this layer is most prone to, and the one it is least able
to see.

**The security gate is deliberately not a receipt.** A receipt recording that a
review happened is the obvious shape and this repository already built and
deleted it: `permission-security/03-review-gate.py` invalidated every receipt it wrote
because the receipts file was tracked, and the model then wrote one asserting a
sign-off that had not happened — *"a forged receipt and a real one are the same
file."* It went out on 2026-08-02 under *"Every hook verifies an artefact. Not
one enforces process."* Every clause of the gate is therefore computable from two
git revisions by anyone, with no state to keep and none to forge. It consumes
`scope.py`'s `sensitive-surface` and `control-surface`, which had been computed
for the risk tier since 2026-08-11 with nothing reading them for security, and it
is what makes `code-review`'s security lens mandatory rather than judged.

**The chain ledger is the audit trail.** `.claude/hooks/state/chain-ledger.jsonl`
is append-only: one row per turn with the derived state and the plan's ticked
task count, plus `kind: "gate"` rows carrying each gate's decision and the user's
reason verbatim. `python tools/chain.py --ledger` reads it back.

**A stall needs three limbs, not two.** The state pinned, the tree churning, *and*
the plan's progress flat. The first version had two and reported `stalled` through
four turns of a healthy twelve-task execution — a detector nobody believes is
worse than none.

## Artifacts and ownership

`TASK.md` and `docs/plans/` — `task-analysis` · `docs/specs/` — `architecture`
· `ISSUES.md` — `debugging` · `LOG.md`, `HANDOFF.md`,
`MEMORY.md`, and `decisions/` — `documentation` · workflow run state — the
repository workflow runner. Chat is not durable evidence.

## Cross-cutting capabilities

Use `research` for external evidence and `debugging` for any failure.
Depth that used to be its own skill now lives in `<skill>/references/` and is read
per task — the artifact review that gates a material spec or plan is
`task-analysis/references/artifact-review.md`, not a skill of its own. Maintain the
capability layer with `capability-layer-maintenance`; it may repair wiring but
never authors product strategy.

## Invariants

- No completion claim without actual evidence from the relevant tree.
- No secrets, unsafe branch operations, or unattended spend.
- No side-effecting release before Gate 2.
- No unresolved review, security, test, scope, or merge finding proceeds.
- No silent retry; every attempt and stop reason is recorded.
- Every unit ends in `documentation` recording or an explicit `BLOCKED` state.

[state:docs-stale]
The durable knowledge artifacts are behind the current workflow run. Resume
`documentation` before claiming the unit complete.
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
capability-layer-maintenance audit and the refactoring layer scan before delivery.
[/state:layer-unreviewed]

[state:chain-stalled]
This unit's state has not advanced for several turns while its tree kept
changing. That is the shape of a **missed handoff**: a stage finished and its
successor was never invoked, which is silent by construction -- the turn ends,
the checks are green, and a skipped stage looks exactly like a stage nothing
needed.

Read the stage table above, find the stage that owns the artefact that just
changed, and invoke its stated successor. If the stage genuinely is still in
progress, nothing is wrong and this will clear on the next transition.

Nothing can force the handoff -- a hook cannot invoke a skill -- so this notice
is the whole mechanism. Acting on it is yours.
[/state:chain-stalled]

[state:entry-direct]
This prompt asks what the current tree already contains -- what something does,
where it lives, how it works. **Answer it directly.** Read what you need, say
what is true, stop.

No procedure applies, so load none. No plan, no gate, no checks, no record: a
question that changes nothing has nothing to verify and nothing to log. This is
the cheapest path there is and it is the correct one far more often than the
shape of this repository suggests.

Two questions wear the same grammar and are **not** this:

- **Recall of a past decision or session** -- what the durable record says,
  rather than what the code says. The stage that owns those records answers it.
- **What other teams or projects do** -- outside evidence, gathered rather than
  read.

If answering turns out to need a change, that is a new prompt and it re-enters
at the stage table above.
[/state:entry-direct]

[state:entry-small]
This prompt names a change small enough that framing it costs more than doing
it -- a named file, a concrete value, a rename, a typo, a version bump. **The
small-work path above applies**: frame it in one line, do it, run the scoped
checks, record one line. No plan, no Gate 1, no separate sweep or review pass;
read your own diff before you stop.

Say **"small path"** out loud, so the choice is visible and reversible.

Three things veto it, and the first two are cheap to check before starting:

1. A **control or shared surface** -- anything under the agent layer, a hook, a
   settings file, a check definition, or a module most of the tree imports.
   These change what fires for every later change.
2. A **sensitive surface** -- auth, credentials, permissions, personal data.
3. The work turning out `major` once there is a diff. `tools/scope.py` is the
   arbiter and it refuses to narrow what it cannot classify; anything it calls
   `major` re-enters at stage 1 mid-flight, which is expected rather than a
   failure.

If any veto fires, take the full chain from the stage table above.
[/state:entry-small]

[state:chain-stalled-no-plan]
The state has been pinned for several turns while the tree kept changing, and
this unit has no active plan -- so two of the three signals fired and the third
could not be asked. This is **weaker evidence than a missed handoff**, and it is
shown rather than suppressed because going quiet would blind the detector to
exactly the units the small-work path above makes routine.

Three things produce it, and only the first is a problem:

1. A unit that finished a stage without invoking the successor -- the real
   missed handoff. Read the stage table above and invoke it.
2. Work taken on the small-work path, which by design has no plan to tick.
   Nothing is wrong; this clears when the work lands.
3. State derived from a **finished** unit's slug, because the branch name still
   points at it. Run tools/resume.py: if the slug names work that is already
   complete, this notice is about that unit and not about what you are doing.

Case 3 repeats every turn until the branch is delivered or the current work gets
a plan of its own, so recognise it once rather than re-reading it.
[/state:chain-stalled-no-plan]

[state:entry-unframed]
This prompt names work with a done-state, and the **Entry** table above routes
named work at any scope to stage 1 `task-analysis`. Frame it first: six fields,
every inferred one marked, no dialogue -- Gate 1 is the plan, not the brief. Then
continue through its Stage B and Stage C in the same turn. If the work turns out
too small to plan, say "too small to plan" and just do it.
[/state:entry-unframed]

[state:entry-open]
This prompt names work whose approach is **not settled**. It still enters at
stage 1 `task-analysis` -- there is one door as of 2026-08-09 -- but the first
thing that skill does with an undecided approach is dispatch 2 `architecture`,
*before* `TASK.md` is written. Order matters and is the whole point: a finished
brief commits Goal and Outputs to one solution shape, and that anchor is what
stage 2 exists to prevent. `architecture` returns here; it is a dispatch, not a
handoff.
[/state:entry-open]

## The entry boundary

The chain assumes a repository somebody has read. When it is dropped into one
nobody has, that assumption is the first thing to fail, and it fails quietly:
stage 1 frames a *request*, so a brief written against an unread codebase looks
exactly like a brief written against a known one.

`repository-navigation` owns that boundary. It runs before stage 1 when there is real code
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
| Comprehend | `repository-navigation` | an unread or half-finished repository, at the entry boundary |
| Research | `research` | external evidence |
| Design | `architecture` | a user-facing surface with no design contract; produces `DESIGN.md` |
| Diagnose | `debugging` | root-cause and bounded recovery |
| Maintain | `capability-layer-maintenance` | layer contracts and wiring |
| Analyze | `data-analysis` | a cost/quality/behavior question this layer's own telemetry can answer |
| Secure | `security` | the deterministic security gate and independent review, at the high risk tier |
| Ground engineering practice | `engineering-standards` | backend, frontend, and fullstack implementation, diagnosis, and scaling, grounded in current industry practice for whatever stack the target repo actually uses |
