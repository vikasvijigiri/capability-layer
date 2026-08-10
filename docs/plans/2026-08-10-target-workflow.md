# Target Workflow Architecture Implementation Plan

**Goal:** the specified chain running end to end — decompose, one workflow per
task, plan in plan mode, Gate 1, execute with minimal diffs, verify, bounded
retry, scoped sweep and review, confirmed push, Gate 2, release, record.

**Source brief:** `TASK.md`, "Make the layer match the target workflow architecture"

**Slug:** target-workflow

**Architecture:** ~70% of the target already exists. This plan corrects one live
defect, proves one mechanism that has never worked, and builds four things —
scope decision, scoped sweep/review/tests, minimal-diff enforcement, plan-mode
wiring. It follows the layer's dominant shape throughout: a tool computes facts
and refuses to decide (`resume.py`, `analyze.py`, `git_identity.py`,
`delivery_check.py`), and a skill reads it.

**Tech stack and constraints:** Python 3.11+, stdlib plus `git` and `gh`, no new
dependency. Windows-first (`PYTHONIOENCODING=utf-8`). Two lifecycle gates only.
The retry budget stays class-aware. A skipped check is named, never counted.

## Sequenced by risk, and Task 3 is a fork

The order is not dependency order alone. **Task 3 is a decision point:** it is
the first live parallel dispatch this repository has ever completed. `HANDOFF.md`
at `0c45d2f` records that the only previous attempt failed because every worktree
based on `main` rather than the working branch.

If Task 3 comes back red, the honest response is to **record the failure and
delete the claim** — `parallel-dispatch.md` currently describes a mechanism that
has not worked, and a second unproven description is worse than none. Tasks 4-10
do not depend on parallelism and proceed either way. **A red Task 3 is a finding,
not a retry.**

## What is already better than the specification

Two things the target under-specifies, which must not be regressed:

| Spec says | Layer has | Why it is better |
|---|---|---|
| "retry (x3 max)" | `FAILURE_BUDGETS = {security 0, merge 2, transient 2, deterministic 3, unknown 3}` | A locked file and a type error are different failures; a flat 3 spends the same budget on both, and a security finding must get zero |
| "probably another gate here for merging" | An `AskUserQuestion` in `delivering` with **no** `<!-- GATE n -->` marker | A third lifecycle gate would break the two-gate rule the same spec asks for. An operational safety check authorises one irreversible act without becoming a stage |

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `tools/parallel_groups.py` | Modify | `normalise()` stops eating a leading dot |
| `tools/test_parallel_groups.py` | Modify | The dotfile case, red first |
| `tools/worktree.py` | Create | Create/remove a worktree on a **mandatory explicit base** |
| `tools/test_worktree.py` | Create | Base is proved by `merge-base --is-ancestor`, not by the call succeeding |
| `.claude/skills/executing-plans/references/parallel-dispatch.md` | Modify | Records the proof, or records the deletion |
| `tools/scope.py` | Create | The small-vs-major decision, computed |
| `tools/test_scope.py` | Create | One case per veto clause, each red first |
| `tools/run_checks.py` | Modify | `--scoped` selects suites and prints `PARTIAL PASS` |
| `tools/test_no_slop.py` | Modify | A fourth scope, `change` |
| `.claude/skills/code-review/SKILL.md` | Modify | Reads the scope decision |
| `.claude/hooks/_hooklib.py` | Modify | Minimal-diff gate for the auto-commit |
| `.claude/skills/writing-plans/SKILL.md` | Modify | Gate 1 becomes `ExitPlanMode` |
| `tools/test_process_router.py` | Modify | Per-gate-tool assertion; the scope contracts |
| `.claude/workflow.md`, `CLAUDE.md` | Modify | Policy, written last |

## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [x] Task 1 — `normalise()` stops eating a leading dot
- [x] Task 2 — `tools/worktree.py`, mandatory explicit base
- [ ] Task 3 — one live parallel dispatch, proved by reading the tree
- [x] Task 4 — `tools/scope.py`, the small-vs-major decision
- [ ] Task 5 — `run_checks.py --scoped` and the `change` sweep scope
- [ ] Task 6 — `code-review` reads the scope decision
- [ ] Task 7 — minimal-diff enforcement
- [ ] Task 8 — Gate 1 becomes plan mode's own approval
- [ ] Task 9 — contracts and policy

## Tasks

### Task 1: `normalise()` stops eating a leading dot

**Purpose:** the scheduler currently cannot see `.claude/settings.json` or
`.github/workflows/*` as shared surfaces, so tasks that collide on them are
scheduled as disjoint.

**Files:**
- Modify: `tools/parallel_groups.py:normalise` — `strip(",;.")` becomes `rstrip(",;.")`
- Modify: `tools/test_parallel_groups.py` — the dotfile case

**Depends on:** none

**Implementation notes:**
- `str.strip` strips **both** ends. Measured on `main`:
  `.claude/settings.json` → `claude/settings.json` → `shared=False`, and
  `.github/workflows/checks.yml` → `github/workflows/checks.yml` → `shared=False`.
- One character. The trailing strip exists so a path written `a.py,` in prose
  parses; nothing needs the leading one.
- This is first because every later task's scheduling correctness rests on it,
  and because it is the module's own documented worst failure: an under-reported
  file set makes colliding tasks look disjoint.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_parallel_groups.py && PYTHONIOENCODING=utf-8 python tools/parallel_groups.py docs/plans/2026-08-10-target-workflow.md`
- Expect: the suite exits 0; the schedule reports at least one group that **must
  not** run concurrently, because Tasks 5 and 7 declare shared surfaces

**Done when:** reverting the one character turns the new case red, and the
scheduler reports the shared-surface serialisation it previously missed.

### Task 2: `tools/worktree.py`, mandatory explicit base

**Purpose:** the one fan-out ever attempted failed because every worktree based
on `main` instead of the working branch. The convenient default *is* the bug.

**Files:**
- Create: `tools/worktree.py` — `create(root, name, base)`, `remove(root, name)`, `main()`
- Create: `tools/test_worktree.py` — base proved by ancestry, not by exit code
- Modify: `.claude/project-checks.json` — register the new suite

**Depends on:** none

**Amended during execution (2026-08-10):** `.claude/project-checks.json` was
declared only by Task 5, but a suite that is not registered never runs, and this
plan's own Task 9 verification is "no check reported as skipped". Registration
lands with the suite that needs it — the same correction the `delivery-check`
plan made for the same reason. The file stays a shared surface, so Tasks 2 and 5
must not run concurrently; `parallel_groups.py` now sees that, which is Task 1.

**Implementation notes:**
- `base` is a **required positional**, never defaulted. A default is what failed.
- `create()` returns the worktree path and the resolved base SHA. The caller gets
  the SHA so it can assert on it rather than trust the call.
- Refuse a base that does not resolve; refuse a name that already exists as a
  worktree; both with a named reason on stderr.
- `remove()` is idempotent and never touches a path outside `root`. Reuse
  `delivery_check._contained` if importable, or restate the containment check —
  a crafted name must not delete outside the repository.
- The suite creates real worktrees in a temp clone and tears them down in a
  `finally`; an in-place mutation without a guaranteed restore left a mutated
  file on disk earlier in this repository's history.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_worktree.py`
- Expect: exit 0, including a case asserting
  `git merge-base --is-ancestor <base> <worktree HEAD>` and a case where a
  worktree requested on a stale base is **refused**

**Done when:** a worktree cannot be created without naming its base, and the
suite proves the base by ancestry rather than by the command returning 0.

### Task 3: one live parallel dispatch, proved by reading the tree

**Purpose:** the fork. Either this repository can run two agents concurrently on
disjoint files, or it cannot and the claim is deleted.

**Files:**
- Modify: `.claude/skills/executing-plans/references/parallel-dispatch.md` — records the outcome either way

**Depends on:** 2

**Implementation notes:**
- Two `task-implementer` agents, dispatched in one message, on **declared
  disjoint files**, each given a worktree from Task 2 with an explicit base.
- **The evidence is the tree, not the report.** An agent saying `DONE` is not
  proof; `git merge-base --is-ancestor <working branch> <worktree HEAD>` and the
  actual diff are.
- If it fails: write what failed and why into the reference, delete the
  instructions that describe the mechanism as working, and stop. Do not retry —
  `tools/loop.py --agent-status BLOCKED --attempt 1` escalates once and never
  re-dispatches unchanged, and this is the same principle at the mechanism level.
- Record the outcome in `ISSUES.md` via `systematic-debugging` if red.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python -c "import subprocess;print(subprocess.run(['git','merge-base','--is-ancestor','feat/target-workflow','HEAD'],capture_output=True).returncode)"` in each worktree, plus `git diff --stat` read directly
- Expect: returncode `0` from each worktree, and two diffs touching disjoint
  declared files

**Done when:** the reference states the measured outcome with the command that
produced it — proved, or deleted and said so.

### Task 4: `tools/scope.py`, the small-vs-major decision

**Purpose:** "small" and "major" must be computed, not judged. Under pressure the
judged answer is always "small".

**Files:**
- Create: `tools/scope.py` — `classify(facts) -> dict`, `gather(root, base)`, `main()`
- Create: `tools/test_scope.py` — one case per clause, each red first

**Depends on:** none

**Implementation notes:**
- A **veto list**, not a score: any clause firing forces `major`, and **every**
  firing clause is collected and named so "why was this major" is readable.
  A weighted score lets two cheap signals outvote one expensive one and turns the
  answer into arithmetic nobody can audit.
- The clauses, each importing its source rather than copying it:
  - **shared surface** — `_hooklib.MIGRATION_PATH_PATTERNS` + `parallel_groups.SHARED_PATTERNS`
  - **control surface** — `.claude/hooks/**`, `.claude/agents/**`, `workflow.md`, `constitution.md`
  - **volume** — more than 8 changed files with a code suffix
  - **spread** — code files spanning more than one top-level container
  - **unmapped** — a changed code path matching no `test_map` rule
- **8 is measured, not picked.** Re-measure before lowering; state the
  distribution in the module docstring, as `BREADTH_WORDS` does.
- `classify` is pure; `gather` does the IO behind an `offline` seam.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_scope.py`
- Expect: exit 0, one `OK:` per clause, and a case proving that inverting any
  single clause's fact flips the verdict to `major` and names that clause

**Done when:** every clause is independently provable, and a change firing
nothing classifies `small` with the clauses it considered listed.

### Task 5: `run_checks.py --scoped` and the `change` sweep scope

**Purpose:** small work runs fewer checks — and says exactly which it skipped.

**Files:**
- Modify: `tools/run_checks.py` — `--scoped` selects suites from a `test_map`
- Modify: `tools/test_no_slop.py` — a fourth scope, `change`
- Modify: `.claude/project-checks.json` — the `test_map` lives here, beside the suites

**Depends on:** 1, 4

**Implementation notes:**
- **`PARTIAL PASS`, never `PASS`.** A scoped run prints the suites it ran *and*
  every suite it skipped, by name. This is the whole safety argument: "fast" must
  mean "ran fewer checks and said which", never "reported green on less
  evidence".
- A scoped run **never** moves `refs/uaios/green/<slug>`. The green ref means the
  full tier passed; a partial run has not earned it.
- `--scoped` on a change `scope.py` calls `major` **exits 2** and refuses to
  narrow. Refusing is the point.
- An unmapped path escalates to the full tier rather than running nothing — the
  map's gaps must fail safe.
- `no-slop --scope change` sweeps only the changed files, and its report names
  the scope so a clean result is not read as a repo-wide clean.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --scoped --tier fast && PYTHONIOENCODING=utf-8 python tools/test_no_slop.py --scope change`
- Expect: the scoped run prints `PARTIAL PASS`, lists every skipped suite by
  name, and the sweep reports the scope in its verdict line

**Done when:** a scoped run cannot print `PASS`, cannot move the green ref, and
refuses a `major` change with exit 2.

### Task 6: `code-review` reads the scope decision

**Purpose:** the review's breadth follows the same computed decision, so "local"
and "global" mean one thing across the layer.

**Files:**
- Modify: `.claude/skills/code-review/SKILL.md` — a scope step and its reason

**Depends on:** 4

**Implementation notes:**
- `small` reviews the changed files and their direct callers; `major` reviews the
  whole branch diff as today.
- **The lens table is unchanged.** Choosing a lens is a reading, not a
  computation, and the skill already says so.
- A `small` review states its scope in the verdict, so `passed: true` is never
  read as broader than it was. Four review rounds on `delivery_check.py` each
  found what the previous missed; a narrowed review must not hide that.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0, including the new assertion that `code-review` names
  `tools/scope.py` and states that a scoped verdict declares its scope

**Done when:** the skill names the scope tool and the suite asserts it.

### Task 7: minimal-diff enforcement

**Purpose:** the target says commits must be minimal-diff, mandatorily. Nothing
enforces it today.

**Files:**
- Modify: `.claude/hooks/_hooklib.py` — the gate and its threshold
- Modify: `tools/test_artifact_autocommit.py` — the gate, red first

**Depends on:** 4

**Implementation notes:**
- The auto-commit already refuses on branch, size (`MAX_FILES = 25`), secrets,
  checks, unverified code, migration and attribution. This is one more clause in
  a mechanism that exists, not a new mechanism.
- **Minimal means "no unrelated file"**, not "few lines". A formatting sweep
  across forty files is not minimal; a hundred-line change in one file is.
  The check: every changed path is one the current `TASK.md` or plan names, or
  the commit is refused with the unnamed paths listed.
- A refusal is always spoken, like every other clause.

**Resolved at Gate 1 — refuse, and name the unrelated paths.** Every other
clause in this gate refuses: branch, size, secrets, checks, unverified code,
migration, attribution. A warning among seven refusals is the one clause nobody
reads, and the specification called minimal-diff mandatory.

The accepted cost is real and stated: a turn touching a file the plan does not
name gets **no checkpoint at all**. The refusal must therefore print the unnamed
paths, so the fix is to name them in the plan or to stop touching them — never to
wonder why nothing committed. Silence here would be the worst outcome of the
three, which is why the printed list is part of the requirement rather than a
nicety.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_artifact_autocommit.py`
- Expect: exit 0, including a case where a commit containing a file named by
  neither `TASK.md` nor the plan is refused and the unnamed path is printed

**Done when:** the gate refuses an unrelated file by name, and the refusal is
visible in the hook's output rather than silent.

### Task 8: Gate 1 becomes plan mode's own approval

**Purpose:** `ExitPlanMode` *"inherently requests user approval"* and explicitly
says not to use `AskUserQuestion` for it. One mechanism, not two.

**Files:**
- Modify: `.claude/skills/writing-plans/SKILL.md` — Gate 1 becomes `ExitPlanMode`
- Modify: `tools/test_process_router.py` — the gate assertion becomes per-gate-tool

**Depends on:** 9

**Implementation notes:**
- `ExitPlanMode` **replaces** the Gate 1 `AskUserQuestion`; the two must never
  coexist, or the plan is approved twice and one of them is theatre.
- Plan mode is read-only apart from its plan file, so **Stage A writes `TASK.md`
  immediately after the exit**, as the first act of stage 3. Ownership is
  unchanged; only the moment moves. The alternative — stage 1 stops producing
  `TASK.md` — was rejected because `session-start/02-bootstrap-docs.py` reads it.
- The `<!-- GATE 1 -->` marker **stays**. The count stays two. The assertion
  changes from "a marker has `AskUserQuestion` behind it" to "a marker has **its
  gate's tool** behind it": `ExitPlanMode` for Gate 1, `AskUserQuestion` for
  Gate 2.
- **No task changes permission mode.** There is no tool for it; exiting plan mode
  returns to whatever was active before. Any text claiming otherwise is wrong.
- The failure mode to avoid: removing the `AskUserQuestion` without updating the
  assertion leaves a marker with no call behind it — a gate that reads as a gate
  and stops nothing. This task owns both, which is why it depends on Task 9.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0, with exactly two `<!-- GATE n -->` markers and each backed by
  its own tool

**Done when:** Gate 1 has `ExitPlanMode` and no `AskUserQuestion`, Gate 2 is
unchanged, and the suite proves both.

### Task 9: contracts and policy

**Purpose:** every rule this plan adds has an assertion, and the policy files
describe what was built rather than what was intended.

**Files:**
- Modify: `tools/test_process_router.py` — the scope and gate contracts
- Modify: `.claude/workflow.md` — the scope decision as policy
- Modify: `CLAUDE.md` — the commit loop gains the scoped tier

**Depends on:** 5, 6, 7

**Implementation notes:**
- Prose last, so it describes the mechanism rather than predicting it. This
  repository's most-repeated defect is a document asserting what the wiring does
  not do.
- Assert: a scoped run cannot print `PASS`; `code-review` names the scope tool;
  the gate markers number two and each has its own tool behind it.
- State the ceiling plainly in `workflow.md`: the chain is a sequence of skill
  invocations, each naming its successor, and **nothing forces the handoff**.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS` with the suite count, and no check reported as skipped

**Done when:** the full tier is green and every rule above has an assertion
behind it.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Tasks 1, 2, 4 and 7 write the case before the change
- [x] III Smallest change — three new tools; every other change edits a file that already owns the concern
- [x] IV Reversibility — nothing pushes, merges or deploys; `worktree.py` tears down what it creates
- [x] V No silent degradation — a scoped run prints `PARTIAL PASS`, names every skipped suite, never moves the green ref, and refuses a major change
- [x] VI Mechanism — Task 9 is the point: every rule here has an assertion
- [x] VII Secrets — no credential enters the repo

## Complexity tracking

No unticked boxes.

## Risks

- **Task 3 may fail, and that is a legitimate outcome.** Parallel dispatch has
  never worked here. If the worktrees still base wrongly, the plan's response is
  to delete the claim rather than retry — a second unproven description is worse
  than none.
- **The `test_map` is a coverage claim nothing proves.** Task 5 asserts the map's
  *shape* — every mapped command is a real suite, every unmapped path escalates.
  It cannot assert the map's *judgement*. A wrongly-mapped path makes small
  changes fast and under-checked, and that failure is silent.
- **Minimal-diff may fight exploratory work.** The marker in Task 7 is real: a
  refusing gate can leave a turn's work uncheckpointed, which is the opposite of
  what the auto-commit exists for.
- **Task 8 changes the approval mechanism**, and its failure mode is a gate that
  stops asking. It owns both the skill and the assertion for that reason.
- **Nine tasks is a large unit.** The Terraform argument applies — approve the
  graph, not the nodes — but Task 3 is a genuine fork and its red path deletes
  scope rather than adding it.

## Approved

2026-08-10. Gate 1 passed. Minimal-diff resolved as refuse-and-name; the cost —
an unplanned file leaves the turn uncheckpointed — is accepted on condition the
refusal names the paths.
