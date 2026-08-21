# Permanent branch-per-parallel-task policy — Implementation Plan

## Context

Every plan in this repository's history has executed serially, even when its
own tasks were genuinely independent, because `executing-plans/SKILL.md`
gates concurrent subagent dispatch behind an explicit per-run request that
nobody has ever made ("Only when parallel dispatch was explicitly chosen for
this run"). The user asked, mid-session, to make parallel dispatch the
**permanent default** for independent tasks, with each task landing on its
own branch, pushed, and opened as its own PR — and, since this repository
has a hard, tested invariant that no skill may ever execute a merge
("`tools/test_process_router.py`: no skill in this layer runs `gh pr merge`;
a human presses the button"), to gate the actual merge into `main` behind
**one batched human approval** covering every PR from a round, rather than
one approval per PR or full automatic merging.

## Approved

**Goal:** Make branch-per-independent-task the permanent, automatic
execution policy in `executing-plans`, with automatic push and PR-creation
per task, and gate the merge step behind one batched confirmation per round
instead of N — without weakening `test_process_router.py`'s existing
no-auto-merge invariant or `delivering`'s existing per-instance push
confirmation for every OTHER kind of push.

**Constraints:** No skill or `tools/*.py` file may contain the literal phrase
`gh pr merge` on an ungated line (`test_process_router.py`'s `_MERGE_VERBS`
check; do not weaken it). No subagent may commit, push, or merge — the
dispatcher (the orchestrating `executing-plans` context) owns all of that,
per `references/parallel-dispatch.md`'s existing "Never let an agent commit,
push or merge" rule and `task-implementer.md`'s existing "Never commit, push,
merge or deploy." A worktree's base must be named explicitly and verified by
`git merge-base --is-ancestor`, never assumed (`tools/worktree.py`'s existing
discipline). The existing detached-worktree default (`tools/worktree.py`
`create()` with no `branch` argument) must stay byte-identical for every
existing caller — this plan only *adds* a branch mode. Merging still requires
one live human approval every time it fires (batched, never a standing
pre-authorization) — matches `delivering/SKILL.md`'s existing "Say the word
and I'll push' is not approval" rule, just applied once per round of PRs
instead of once per PR. Before any branch merges, its diff (combined across
the round) goes through one scoped `no-slop` + `code-review` pass — resolved
this session: task-level verification alone gates the PR opening (fast), but
review still gates the merge, batched across the round rather than
per-branch.

**Input:** `.claude/skills/executing-plans/SKILL.md` (the opt-in clause to
remove); `.claude/skills/executing-plans/references/parallel-dispatch.md`
and `references/using-git-worktrees.md` (read in full this session);
`tools/worktree.py` + `tools/test_worktree.py` (read in full — `create()`
always detaches today, by explicit design comment); `.claude/agents/
task-implementer.md` (dispatcher owns delivery, unchanged); `tools/
parallel_groups.py` (already computes real concurrent rounds, two live
parsing bugs fixed this session, now green — build on it, not part of this
plan); `.claude/skills/delivering/SKILL.md` (owns "push, PR and merge" per
`OUTWARD_SKILLS` in `test_process_router.py`; "The push confirmation"
section, lines 82-108); `tools/test_process_router.py` (`_MERGE_VERBS`
check, ~line 1037-1100; `OUTWARD_SKILLS` dict); `.claude/workflow.md`
("Parallelism and integration" section, already claims "Each implementation
task gets its own worktree **and branch**" — the code does not honor that
today; also "It never skips [approval]... the one rule in this layer with no
exceptions").

**Output:** `tools/worktree.py` gains an additive branch-creation mode;
`executing-plans/SKILL.md`'s parallel-dispatch section rewritten so
concurrent dispatch is the default whenever `tools/parallel_groups.py`
reports concurrency > 1, with automatic per-task branch, push, and PR;
`delivering/SKILL.md` gains a narrowly-scoped exception for this exact case
plus the batched-merge mechanism; `tools/test_process_router.py` gains
assertions pinning the new exception's scope; `.claude/workflow.md`
reconciled; one `decisions/` ADR recording the policy and why.

**Done Checks:** `python tools/test_worktree.py` exits 0 including new
branch-mode cases; `python tools/test_process_router.py` exits 0 including
new scope-pinning assertions and the existing `_MERGE_VERBS` check
unweakened; `python tools/run_checks.py --tier all --require-test` exits 0.

**Out of Scope:** actually dispatching and merging a real parallel round in
this session (that is the NEXT unit, using this policy on the already
Gate-1-approved `docs/plans/2026-08-21-four-more-spec-metrics.md`); changing
`task-implementer.md`'s `isolation: worktree` frontmatter or resolving the
pre-existing, separately-documented ambiguity about whether that harness
feature reliably resolves its own base (`parallel-dispatch.md`'s own
"own the worktree instead of asking for one" remedy already routes around
it — unchanged by this plan); a fully-serial plan's behavior (unaffected —
this policy only fires for a round `parallel_groups.py` proves has
concurrency > 1); building a stacked-PR or rebase mechanism for a plan whose
later round depends on an earlier parallel round's output (resolved simply:
that later round is blocked until the earlier round's batched merge lands,
same as any other cross-round dependency today).

**Slug:** `parallel-branch-policy`

**Risk:** high (inferred — confirm with `python tools/scope.py --plan
docs/plans/2026-08-21-parallel-branch-policy.md` once saved; every touched
file matches `CONTROL_PATTERNS`: `.claude/skills/*`, `.claude/agents/*`,
`.claude/workflow.md`, `tools/*.py`). Not permission to skip the merge
confirmation — `workflow.md` is explicit that the risk tier "never skips"
approval.

**Blast radius:** every future plan whose tasks `parallel_groups.py` proves
independent now executes differently (concurrently, on separate branches,
each auto-pushed and PR'd) instead of serially on one branch. `delivering`'s
push-confirmation behavior changes for this one case only. No change to any
fully-serial plan, to `task-implementer`'s own contract, or to
`_MERGE_VERBS`'s enforcement.

**Rollback:** five independent, additive-where-possible commits (one per
task below); revert any one without breaking the others, since Task 1 (the
worktree branch mode) is additive and inert until Task 2 calls it. Reverting
Tasks 2-4 alone restores today's serial-only, per-instance-confirmed
behavior exactly, since the underlying scheduler and worktree tool are
unchanged.

**Architecture:** `tools/parallel_groups.py` already decides *whether* a
round may run concurrently (unchanged by this plan). This plan changes what
`executing-plans` *does* with a `yes`: instead of a rule requiring an
explicit per-run ask, concurrency becomes the default action; instead of
each task's worktree being a detached scratch surface the dispatcher later
folds back into one branch, each gets `tools/worktree.py`'s new named-branch
mode so its work is independently pushable; instead of one delivery at the
very end of the whole 9-stage chain, `delivering`'s push/PR/merge machinery
fires once per parallel round, with push+PR automatic and only the merge
step still asking — batched into one question instead of N. Nothing about
Gate 1 (plan approval) or the fully-serial path changes.

**Tech stack and constraints:** Python 3, stdlib + existing `git`/`gh`
subprocess patterns already used by `tools/worktree.py` and `delivering`;
GitHub MCP tool `mcp__github__merge_pull_request` for the actual merge
action (never the `gh pr merge` CLI phrase in skill prose, per the Hard
Constraint below).

## Grounding

- `executing-plans/SKILL.md`'s "## Dispatching subagents for parallel
  tasks" section, verbatim: "Only when parallel dispatch was explicitly
  chosen for this run — that choice is the ask; do not spawn agents
  otherwise." This is the single clause responsible for every plan in this
  repo's history running serially.
- `tools/worktree.py`'s `create()` (read in full): always `git worktree add
  --detach`, by explicit design — "a named branch per worktree leaves
  branches behind after teardown." It "creates and removes; it decides
  nothing. No branch is pushed, no commit is made, nothing is merged."
- `references/parallel-dispatch.md`'s Constraints (read in full this
  session): "**Never let an agent commit, push or merge.** The dispatcher
  owns integration" and "The remedy is to own the worktree instead of
  asking for one" — i.e. today's actual practice is already
  `python tools/worktree.py create <name> <base>` called by the dispatcher
  itself, not the harness's automatic `isolation: worktree`. This plan's
  Task 2 extends that exact, already-practiced call with a `--branch` flag.
- `test_process_router.py`'s `_MERGE_VERBS` (read in full): fails any
  skill/command/non-test `tools/*.py` line containing `gh pr merge` without
  a negation word. `OUTWARD_SKILLS = {"delivering": "push, PR and merge",
  "releasing": "deploy"}` — confirms `delivering` is the correct owner for
  the new push/PR/merge-batch logic, not `executing-plans` itself; Task 2
  therefore only creates and populates branches, Task 3/4 do the outward
  actions.
- `delivering/SKILL.md:82-108` ("The push confirmation", read in full):
  requires a fresh `AskUserQuestion` before every push, PR, or merge,
  individually; explicitly bans a standing pre-authorization. `workflow.md`
  confirms this is *not* the numbered "Gate 2" (which is release-candidate
  approval after stage 8) — `delivering`'s own text calls it "an operational
  safety check... no `<!-- GATE n -->` marker, so the gate set below is
  still exactly two." This plan's batching therefore batches an *operational
  safety check*, not a numbered gate — corrected from an earlier
  mis-framing during this session's own research.
- `.claude/workflow.md`'s "Parallelism and integration" section already
  says "Each implementation task gets its own worktree and branch" — the
  code has never honored the "and branch" half. This plan makes the claim
  true rather than introducing a new one.
- `python tools/memory.py --paths executing-plans/SKILL.md delivering/
  SKILL.md worktree.py test_process_router.py workflow.md task-implementer.md`
  → 30 entries, all directory-level; `decisions/2026-08-02-gate-on-
  blast-radius.md` and `decisions/2026-08-09-one-door-into-the-chain.md`
  are the closest precedent (gating by actual risk/surface, one entry point
  into the chain) and neither conflicts with this design.
- Resolved by `AskUserQuestion` this session: a task's PR opens right after
  its own task-level verification (fast); review (`no-slop` + `code-review`,
  scoped, run once over the round's combined diff) gates the merge, not the
  PR-open.

## File map

- Modify: `tools/worktree.py` — additive `branch` parameter on `create()`
  and a `--branch` CLI flag.
- Modify: `tools/test_worktree.py` — regression cases for the new mode; the
  existing detached-mode cases must stay green unchanged.
- Modify: `.claude/skills/executing-plans/SKILL.md` — parallel dispatch
  becomes the default; per-task branch creation via the new worktree mode;
  dispatcher-owned commit per verified task.
- Modify: `.claude/skills/executing-plans/references/parallel-dispatch.md`
  — document the new branch-per-task step in the existing "Running it"
  flow (small addition, not a rewrite).
- Modify: `.claude/skills/delivering/SKILL.md` — narrow, explicitly-scoped
  exception to "The push confirmation" for a parallel round's task
  branches (push + PR automatic); new batched-merge mechanism (one
  `AskUserQuestion` naming every PR in the round; on approval, merge each
  via `mcp__github__merge_pull_request`, respecting the existing
  squash-vs-stack warning).
- Modify: `tools/test_process_router.py` — assertions pinning the new
  exception's scope (it must name "parallel" explicitly, so a later edit
  cannot silently broaden it into the general push confirmation).
- Modify: `.claude/workflow.md` — "Parallelism and integration" section
  updated to describe the now-true default-parallel, batched-approval
  behavior.
- Create: `decisions/2026-08-21-branch-per-parallel-task.md` — the ADR.

## Progress
- [x] Task 1 — `tools/worktree.py` branch-creation mode. **Executed:**
  `python tools/test_worktree.py` -> `All worktree tests passed` (22
  cases, 6 new for branch mode), default detached path unchanged.
- [x] Task 2 — `executing-plans`: parallel dispatch becomes the default, with
  per-task branches. **Executed:** `python tools/analyze.py --slug
  parallel-branch-policy` -> `consistent -- 6 task(s), no findings`;
  `python tools/test_referenced_paths.py` -> `All referenced-path tests
  passed`.
- [x] Task 3 — `delivering`: automatic push + PR per task branch.
  **Executed:** `python tools/analyze.py --slug parallel-branch-policy` ->
  `consistent -- 6 task(s), no findings`; `python
  tools/test_referenced_paths.py` -> `All referenced-path tests passed`.
- [ ] Task 4 — `delivering`: batched merge confirmation and execution
- [ ] Task 5 — `test_process_router.py`: pin the new exception's scope
- [ ] Task 6 — `workflow.md` + ADR

## Tasks

### Task 1: `tools/worktree.py` branch-creation mode
**Purpose:** each parallel task needs a real, named, independently-pushable
branch instead of today's detached-HEAD scratch surface.
**Files:**
- Modify: `tools/worktree.py:create` — add `branch: str | None = None`
  parameter. When given, `git worktree add -b <branch> <target> <sha>`
  instead of `--detach`; on failure (e.g. branch name already in use),
  raise `WorktreeError` naming the branch, same pattern as every other
  refusal in this file. Default behavior (`branch=None`) stays byte-for-byte
  the existing `--detach` call.
- Modify: `tools/worktree.py:main` — add `--branch NAME` optional CLI arg
  on the `create` action, passed through to `create()`.
- Test: `tools/test_worktree.py` — a new case creating a worktree with
  `branch="feat/x"` asserts `git -C <path> rev-parse --abbrev-ref HEAD ==
  "feat/x"` (not detached); the existing detached-mode assertions (path
  exists, base SHA returned, ancestry checks, all four refusal cases) must
  still pass unmodified, proving the default is unchanged.
**Dependencies:** none.
**Implementation notes:** Mirror the existing `_git`/`_contained` error
handling exactly — this is one new branch in an existing `if/else`, not new
plumbing.
**Rollback:** revert the commit; every existing caller is unaffected since
none passes `branch`.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_worktree.py`
- Expect: exit 0, including the new branch-mode case, with every prior
  case still passing.
**Done when:** `python tools/worktree.py create t1 main --branch test/t1`
in a scratch repo produces a worktree whose `HEAD` is a real, named branch,
not detached.

### Task 2: `executing-plans` — parallel dispatch becomes the default, with per-task branches
**Purpose:** remove the requirement that a user ask for parallel dispatch
by name, and give each task in a schedulable round its own branch instead
of a shared detached worktree.
**Files:**
- Modify: `.claude/skills/executing-plans/SKILL.md` — rewrite "##
  Dispatching subagents for parallel tasks": delete "Only when parallel
  dispatch was explicitly chosen for this run"; replace with: run `python
  tools/parallel_groups.py <plan>` before Task 1 of any plan with more than
  one task; for any round it reports with concurrency > 1, dispatch is the
  default — no user ask required. For each task in such a round, the
  dispatcher creates its worktree with `python tools/worktree.py create
  <task-name> <plan-base-branch> --branch <slug>/task-<N>` (base is the
  plan's own branch tip, verified by `git merge-base --is-ancestor` per
  `parallel-dispatch.md`'s existing discipline — never the repository
  default branch). Dispatch one `task-implementer` per task in the round,
  same message, pointed at the pre-created worktree path (not relying on
  the agent's own `isolation: worktree` frontmatter, matching
  `parallel-dispatch.md`'s existing "own the worktree instead of asking for
  one" remedy). After the round, verify each worktree's diff (read it, not
  the agent's self-report) and its task's own Verification command; only
  then does the dispatcher — never the subagent — `git add`/`git commit`
  inside that worktree, on that task's named branch. Hand off the list of
  now-committed branches to `delivering` (Task 3) rather than merging them
  into the plan's own working branch.
- Test: none new (this is a prose/procedure change to a skill; its
  behavior is exercised by actually running a parallel round, deferred to
  the next unit per Out of Scope).
**Dependencies:** 1 (needs the new `--branch` worktree mode to exist).
**Implementation notes:** A fully-serial round (concurrency == 1, or a plan
with `Dependencies:` that force serialization) is completely unaffected —
this section only fires when `parallel_groups.py` itself reports
concurrency > 1 for a round.
**Rollback:** revert the commit; the opt-in clause returns, restoring
today's serial-only default.
**Preconditions:** Task 1 merged/applied first.
**Verification:**
- Run: `python tools/analyze.py --slug parallel-branch-policy` (this
  plan's own mechanical self-check, per `writing-plans` C5)
- Expect: no missing-section or broken-reference findings against the
  edited `SKILL.md`.
**Done when:** the section no longer contains the words "explicitly
chosen", and names the exact `worktree.py create ... --branch` invocation.

### Task 3: `delivering` — automatic push + PR per task branch
**Purpose:** narrowly, explicitly except this one case from "The push
confirmation"'s per-instance `AskUserQuestion` requirement, since each
branch is small, isolated, independently reviewable, and reversible —
nothing merges yet.
**Files:**
- Modify: `.claude/skills/delivering/SKILL.md` — immediately under "The
  push confirmation" heading, add a clearly-labeled subsection ("Exception:
  a parallel round's task branches") stating: for branches created by
  `executing-plans`'s parallel-dispatch step (Task 2 above) specifically,
  `git push` and PR-creation (`gh pr create` or the GitHub MCP
  `create_pull_request`) happen automatically, per branch, with no
  `AskUserQuestion` — because nothing is merged by this step. State the
  scope boundary explicitly: this exception applies ONLY to branches from a
  proven-independent parallel round; every other push in this repository
  keeps requiring the existing per-instance confirmation, unchanged.
- Test: `tools/test_process_router.py` (Task 5, below) pins that this
  exception is scoped by name, not written broadly enough to swallow the
  general rule.
**Dependencies:** 2 (the branches this task pushes are Task 2's output).
**Implementation notes:** Do not touch the existing per-instance
confirmation prose for any other push/PR path — this is a new, additional
subsection, not an edit to the general rule.
**Rollback:** revert the commit; every push reverts to requiring
per-instance confirmation, including a parallel round's branches.
**Preconditions:** Task 2 in place (the exception refers to branches Task 2
creates).
**Verification:**
- Run: `python tools/analyze.py --slug parallel-branch-policy`
- Expect: no broken-reference or missing-section findings.
**Done when:** `delivering/SKILL.md` states, in one place, exactly which
pushes need no per-instance confirmation and why, without altering the
wording of the confirmation requirement for anything else.

### Task 4: `delivering` — batched merge confirmation and execution
**Purpose:** the merge into `main` still needs a live human approval every
time — batched into one question per round instead of N — and the actual
merge action must never be phrased as `gh pr merge` in this file.
**Files:**
- Modify: `.claude/skills/delivering/SKILL.md` — new subsection right
  after Task 3's: once every PR from a round is open, run one scoped
  `no-slop` + `code-review` pass over the round's combined diff (resolved
  this session — review gates the merge, not the PR-open); then present
  ONE `AskUserQuestion` naming every PR (number, branch, one-line summary)
  and asking which, if any, to merge now. On approval, merge each named PR
  using the GitHub MCP tool `mcp__github__merge_pull_request` — never the
  `gh pr merge` CLI phrase — respecting the existing squash-vs-stack
  warning already in this file. On decline or partial approval, state
  plainly which PRs remain open and unmerged; nothing is retried
  automatically.
**Dependencies:** 3 (there must be PRs to batch).
**Implementation notes:** This is still a live, per-invocation approval —
never write anything resembling a standing pre-authorization. The
"operational safety check, not Gate 2" framing from Grounding applies here
too; do not call this "Gate 2" anywhere in the file.
**Rollback:** revert the commit; batching disappears, but nothing about
Task 3's push/PR automation depends on it existing.
**Preconditions:** Task 3 in place.
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exit 0 — `_MERGE_VERBS` finds no ungated `gh pr merge` phrase in
  the edited file (it will contain `mcp__github__merge_pull_request`
  instead, which the regex does not match).
**Done when:** the file describes one batched question covering every PR
in a round, and the merge action is named via the MCP tool, never the CLI
phrase.

### Task 5: `test_process_router.py` — pin the new exception's scope
**Purpose:** "VI Mechanism" — a rule this plan adds must be enforced by a
test, not left as unpinned prose that the next edit can silently widen.
**Files:**
- Modify: `tools/test_process_router.py` — new assertion: the "Exception:
  a parallel round's task branches" subsection in `delivering/SKILL.md`
  exists and contains the word "parallel" within its own heading/first
  line (proving the scoping language is present, not generic); a second
  assertion confirms `_MERGE_VERBS`'s existing scan still reports zero hits
  across every skill/command/tools file after this plan's edits (i.e. the
  suite run itself is the proof — no new exemption is carved into the scan
  logic).
**Dependencies:** 3, 4 (asserts against their output).
**Implementation notes:** Follow the existing style at ~line 1103-1113
(`OUTWARD_SKILLS` loop) for the new assertion — same file, same `check()`
helper, same "the rule is the tool, not the asking" rigor.
**Rollback:** revert the commit; the new behavior stays but loses its test
pin.
**Preconditions:** Tasks 3 and 4 landed (the text to assert against must
exist).
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exit 0, including the two new assertions.
**Done when:** deleting the word "parallel" from the exception's heading
(a manual, temporary test) makes the new assertion fail — proving it
actually pins the scope rather than trivially passing.

### Task 6: `workflow.md` + ADR
**Purpose:** make the standing policy document match the code, and record
why this reverses a previously-deliberate "no branch per worktree" design.
**Files:**
- Modify: `.claude/workflow.md` — "Parallelism and integration" section:
  after "Each implementation task gets its own worktree and branch",
  note that this is now the *default* behavior for any round
  `parallel_groups.py` reports as concurrent, not merely an aspiration;
  one sentence on the batched-merge-confirmation replacing per-PR asks for
  this case, cross-referencing `delivering/SKILL.md`.
- Create: `decisions/2026-08-21-branch-per-parallel-task.md` — records:
  the prior state (opt-in dispatch, detached worktrees only), what changed
  and why (user request; the `_MERGE_VERBS`/no-auto-merge invariant stays
  intact; batching an existing operational safety check rather than adding
  or removing a gate), and the explicit non-goals (no change to fully
  serial plans, no change to `task-implementer`'s contract, no new numbered
  gate).
**Dependencies:** 2, 3, 4 (describes their combined behavior).
**Implementation notes:** Follow the existing `decisions/*.md` format
(see any file in `decisions/` for the header/body shape used throughout
this repository).
**Rollback:** revert the commit; `workflow.md` reverts to describing the
aspiration rather than the implementation, and the ADR is removed.
**Preconditions:** Tasks 2-4 landed (this documents their combined effect).
**Verification:**
- Run: `python tools/run_checks.py --tier all --require-test`
- Expect: exit 0, printing the suite count, with every prior suite
  (including Tasks 1 and 5's new cases) still green.
**Done when:** `workflow.md` no longer states an aspiration the code does
not implement, and the ADR is discoverable from `decisions/`'s own listing.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — Tasks 1 and 5 define their failing cases before the
  behavior; Tasks 2-4 and 6 are prose/policy changes with no new runtime
  behavior of their own to test-first (their combined effect is proven by
  Task 5's assertions and the full suite in Task 6)
- [x] III Smallest change — Task 1 is a single additive parameter; Tasks 3
  and 4 are new subsections beside the existing rule, not rewrites of it
- [x] IV Reversibility — six independent commits, each named with its own
  rollback
- [x] V No silent degradation — the merge step keeps requiring live
  approval every time it fires; nothing here waives that
- [x] VI Mechanism — Task 5 exists specifically because a rule this plan
  adds (the narrow push-confirmation exception) needs a test pinning its
  scope, not just prose
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why

- **Actually dispatching a real parallel round under this new policy.**
  That is the next unit, using the already-approved `docs/plans/
  2026-08-21-four-more-spec-metrics.md` (4 independent tasks, 1 schedulable
  round) as the live test case. This plan only builds the mechanism.
- **`task-implementer.md`'s `isolation: worktree` frontmatter and whether
  the harness's own automatic worktree isolation reliably resolves its
  base.** `parallel-dispatch.md` already documents a working remedy (the
  dispatcher pre-creates the worktree itself) that this plan's Task 2 uses
  unchanged — resolving the underlying harness ambiguity is a separate,
  pre-existing open item, not created or worsened by this plan.
- **A fully-serial plan, or a round `parallel_groups.py` reports as
  concurrency == 1.** Completely unaffected — every mechanism here is
  gated on the scheduler's own output.
- **Stacked-PR or rebase tooling for a later round that depends on an
  earlier parallel round's output.** Resolved simply: that later round
  waits for the earlier round's batched merge, exactly as any cross-round
  dependency already does today.
- **Per-branch `no-slop`/`code-review` before each PR opens.** Resolved by
  `AskUserQuestion` this session in favor of the faster option: task-level
  verification gates the PR-open, one combined review gates the merge.
