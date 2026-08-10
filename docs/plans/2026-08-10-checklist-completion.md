# Checklist Completion Implementation Plan

**Goal:** close every `GOAL_CHECKLIST.md` line that has an honest implementation
in a repository whose deployable artefact is a wheel, and state plainly in this
plan which lines do not.

**Risk:** high — `python tools/scope.py --plan docs/plans/2026-08-10-checklist-completion.md`
reports `high forced by: control-surface, shared-surface` over 35 declared paths,
exit 2. Correct, and not a formality: this plan adds two hooks to per-turn events,
edits `settings.json`, and changes what the commit gate and both approval gates
do. Every one of those changes the behaviour of every later change.

**Source brief:** `GOAL_CHECKLIST.md` (148 lines, 15 stages, supplied by the
user), plus the audit of the layer against all 77 of its lines at
`https://claude.ai/code/artifact/681a1cb1-6c26-4474-9c6f-82a9e039d3ec` —
21 mechanism, 23 partial, 4 prose-only, 29 absent.

**Slug:** checklist-completion

**Branch:** execution starts by cutting `feat/checklist-completion` from the
current `feat/target-workflow` head. The slug keys `tools/resume.py`, and two
plans sharing one slug makes every derived fact ambiguous.

**Architecture:** one reframing carries most of this plan. **The deployable
artefact here is the wheel, and "production" is a target repository with the
layer installed.** That is not a metaphor — `tools/test_package.py` already
builds the wheel, installs it into a clean venv and then into a fresh git repo,
and requires *that* repo's own tier to come back green. So §12's staging
rehearsal exists and needs a report; §13's rollback exists as `install.py
uninstall`, keyed off a sha256 manifest, and the checklist asks for it to be
**executed** rather than documented; `tools/smoke.py` already boots a process and
probes it.

Everything else follows the layer's dominant shape: a tool computes facts and
refuses to decide, and a skill reads it.

**What memory said, and how it changed this plan.** `tools/memory.py --paths`
over the planned files returned 23 entries. Three are binding:

- `decisions/2026-08-07-derived-state-over-stored-state.md` names
  `tools/resume.py`. **Task 1 therefore derives the new state from git facts and
  stores nothing** — a `WAITING_DELIVERY` flag in a state file would be the
  duplicate owner that ADR exists to forbid.
- `decisions/2026-08-04-hooks-never-name-a-skill.md` constrains Tasks 2 and 3:
  the kill switch and the gate log report state keys, and `.claude/workflow.md`
  owns what they mean.
- An `ISSUES.md` entry records that *"two hooks now shell out to
  `.claude/install.py` with near-identical"* logic. Task 7 reuses
  `test_package.py`'s existing rehearsal rather than adding a third caller.

**Tech stack and constraints:** Python 3.11+, stdlib plus `git` and `gh`, no new
runtime dependency. Windows-first (`PYTHONIOENCODING=utf-8`). Two lifecycle gates
only. Class-aware retry budgets stay. A skipped check is named, never counted.
Nothing acquires `gh pr merge`. Every rule added gets a test or a hook, not prose.

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `tools/resume.py` | Modify | Derives `WAITING_DELIVERY` from git facts |
| `tools/test_resume.py` | Modify | The new state, red first |
| `tools/chain.py` | Modify | Treats the new state as a human wait; `record_gate()` |
| `tools/test_chain.py` | Modify | Both, red first |
| `tools/halt.py` | Create | The kill switch: halt, status, resume |
| `tools/test_halt.py` | Create | Halting leaves a resumable tree |
| `.claude/hooks/pre-run/01-halt-guard.py` | Create | Refuses tool use while halted |
| `.claude/hooks/pre-edit/02-agent-scope-guard.py` | Create | Denies a write outside an agent's declared paths |
| `.claude/agents/*.md` | Modify | Each declares `allowed-paths:` |
| `tools/test_agent_standards.py` | Modify | Every agent declares a path scope |
| `tools/run_checks.py` | Modify | `--scoped` also narrows lint to the diff |
| `tools/deps.py` | Create | Licence compliance and an SBOM for declared dependencies |
| `tools/test_deps.py` | Create | A forbidden licence fails; an absent tool is named |
| `tools/release_candidate.py` | Create | Runs the rehearsal, executes rollback, emits the Gate 2 report |
| `tools/test_release_candidate.py` | Create | The report names every fact, and rollback really ran |
| `tools/git_ops.py` | Create | Rebase-before-push, conflict classification, PR body from the plan |
| `tools/test_git_ops.py` | Create | Each, against a real temp repo |
| `tools/budget.py` | Create | Per-unit turn and elapsed ceiling, from the ledger |
| `tools/test_budget.py` | Create | The ceiling escalates rather than running unbounded |
| `.claude/skills/writing-plans/references/task-decomposition.md` | Modify | Task shape gains rollback and preconditions |
| `.claude/skills/writing-plans/references/plan-mode.md` | Modify | Gate 1 records its decision |
| `.claude/skills/releasing/SKILL.md` | Modify | Reads the release-candidate report; Gate 2 records its decision |
| `.claude/skills/delivering/SKILL.md` | Modify | Reads `git_ops.py` |
| `.claude/skills/knowledge-manager/formats.md` | Modify | Recurring-findings capture |
| `tools/analyze.py` | Modify | Requires the new task fields |
| `tools/test_analyze.py` | Modify | The fixture gains them |
| `tools/test_process_router.py` | Modify | Every contract this plan adds |
| `.claude/project-checks.json` | Modify | Registers the new suites and slow-tier checks |
| `.claude/settings.json`, `.claude/hooks/hooks_registry.json` | Modify | Registers the two new hooks |
| `.claude/workflow.md`, `CLAUDE.md`, `README.md` | Modify | Policy, written last |
| `GOAL_CHECKLIST.md` | Modify | Tracked, so the brief is committed with the work |

## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [ ] Task 1 — `WAITING_DELIVERY`, derived not stored
- [ ] Task 2 — the gate log, appended to the ledger
- [ ] Task 3 — the kill switch
- [ ] Task 4 — agent file scope, enforced by a hook
- [ ] Task 5 — SAST on the diff
- [ ] Task 6 — licence compliance and SBOM
- [ ] Task 7 — the release candidate, with rollback executed
- [ ] Task 8 — rollback and preconditions in the task shape
- [ ] Task 9 — git operations
- [ ] Task 10 — a per-unit budget ceiling
- [ ] Task 11 — Gate 1 is reachable, and the plan-mode claim is corrected
- [ ] Task 12 — contracts and policy

## Tasks

### Task 1: `WAITING_DELIVERY`, derived not stored

**Purpose:** `tools/chain.py` currently reports a stall that is a legitimate
human wait. A reviewed branch with no PR is waiting on a person, exactly like the
two gate states — and there is no state for it, so the instrument I shipped
this morning cries wolf on its own repository.

**Files:**
- Modify: `tools/resume.py:derive_state` — a new state between BUILD and LAND
- Modify: `tools/test_resume.py` — the new state, red first

**Depends on:** none

**Implementation notes:**
- **Derive it; store nothing.** `decisions/2026-08-07-derived-state-over-stored-state.md`
  is binding here and names this file. The facts are already gathered: the plan's
  every checkbox ticked, commits ahead of base, and no open PR for the branch.
- Add it to `TERMINAL` and to `NEXT_ACTION` in the same edit — a state with no
  next action is one `resume.py` prints an empty instruction for.
- The wording of the next action is the deliverable a reader acts on: it should
  say a delivery decision is owed, not "waiting".

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_resume.py && PYTHONIOENCODING=utf-8 python tools/resume.py`
- Expect: the suite exits 0 with a case asserting the new state, and the live run
  on this branch reports it rather than `BUILD`

**Done when:** a reviewed, unpushed branch derives `WAITING_DELIVERY`, and
reverting the change makes the new case red.

### Task 2: the gate log, appended to the ledger

**Purpose:** both gates take a decision and neither records it as data. The
checklist asks for decision plus rationale in a gate log; the ledger is already
append-only, so it is the right home rather than a second file.

**Files:**
- Modify: `tools/chain.py` — `record_gate(gate, decision, reason)`; treat Task 1's state as a wait
- Modify: `tools/test_chain.py` — both, red first
- Modify: `.claude/skills/writing-plans/references/plan-mode.md` — Gate 1 records
- Modify: `.claude/skills/releasing/SKILL.md` — Gate 2 records

**Depends on:** 1

**Implementation notes:**
- One entry shape for both gates: `gate`, `decision`, `reason` verbatim, and the
  plan-body hash Gate 1 already computes, so a rejection is traceable to the text
  that was rejected.
- **Verbatim, never paraphrased.** `tools/loop.py` refuses to re-present a plan
  body whose hash has not changed; a summarised rejection produces a second
  submission that looks new and is not.
- The skills record; the hook does not. A hook cannot know a decision was made.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_chain.py && PYTHONIOENCODING=utf-8 python tools/chain.py --ledger`
- Expect: exit 0, a case proving a gate entry survives a later append unmodified,
  and the ledger listing shows gate rows distinguishable from state rows

**Done when:** a gate decision is queryable after the fact, and Task 1's state
no longer reports as stalled.

### Task 3: the kill switch

**Purpose:** nothing halts an in-flight run. The checklist wants one command that
stops work from any state and leaves the tree resumable.

**Files:**
- Create: `tools/halt.py` — `halt(reason)`, `status()`, `resume()`, `main()`
- Create: `tools/test_halt.py` — halting leaves a resumable tree
- Create: `.claude/hooks/pre-run/01-halt-guard.py` — refuses tool use while halted

**Depends on:** none

**Implementation notes:**
- Halt writes a single flag file under `.claude/hooks/state/` — ignored, so it is
  machine-local and cannot be committed by accident. This is the one place a
  stored fact is correct: a halt is an *instruction*, not a derived state.
- The guard **denies** rather than asks, and its message names `tools/halt.py
  --resume`. A halt that can be talked past is not a halt.
- **It must not strand work.** `03-checkpoint.py` already snapshots every turn;
  halting takes no destructive action, so resuming needs no recovery. Assert that
  the tree is byte-identical across halt/resume.
- The guard names no skill.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_halt.py`
- Expect: exit 0, including a case that fires the guard hook under a halt and
  reads `permissionDecision: deny`, and one hashing the tree before and after

**Done when:** a halt denies the next tool call, names how to resume, and leaves
the tree unchanged.

### Task 4: agent file scope, enforced by a hook

**Purpose:** every agent declares a `tools:` allowlist the harness enforces, and
its *file* scope is prompt instruction only. The checklist's least-privilege line
asks for enforcement by hook rather than by prompt, and this session showed why:
an agent respected its declared files and refused to wire a function — correctly,
and nothing would have stopped it.

**Files:**
- Create: `.claude/hooks/pre-edit/02-agent-scope-guard.py` — denies a write outside scope
- Modify: `.claude/agents/task-implementer.md` — declares `allowed-paths:`
- Modify: `tools/test_agent_standards.py` — every writing agent declares one

**Depends on:** none

**Implementation notes:**
- Only agents that write need a scope. `Explore`, `diff-reviewer` and the other
  read-only agents have no `Write`/`Edit` grant and must not be forced to declare
  one — asserting on all eleven would make the check noise.
- The dispatcher passes the round's declared files; the guard reads them from the
  agent frontmatter plus an env var the dispatch sets. **If the scope cannot be
  established, deny** — an unscoped write is the case this exists for.
- Fire it with `tools/run_hook.py` against a realistic payload. A hook bug's
  symptom is silence.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_agent_standards.py && PYTHONIOENCODING=utf-8 python tools/run_hook.py pre-edit '<payload writing outside scope>'`
- Expect: the suite exits 0; the hook returns `deny` for an out-of-scope path and
  is silent for an in-scope one

**Done when:** a write outside a dispatched agent's declared files is denied by a
mechanism, not by instruction.

### Task 5: SAST on the diff

**Purpose:** ruff's `S` rules (bandit, native) run over the whole tree, so a
finding in untouched code blocks a change that did not cause it — and a real
finding in the diff is buried among them.

**Files:**
- Modify: `tools/run_checks.py` — `--scoped` narrows lint to changed files
- Modify: `tools/test_run_checks_scoped.py` — the narrowing, and its refusal

**Depends on:** none

**Implementation notes:**
- Narrow by passing the changed paths to ruff, never by disabling rules.
- **The tree-wide run stays** and is what the full tier uses. This adds a scoped
  view for a `small` change; it does not replace the gate.
- Same discipline as the existing scoped tier: it prints what it skipped.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_run_checks_scoped.py`
- Expect: exit 0, with a case proving the scoped lint set is a subset of the
  tree-wide one and that the skipped remainder is named

**Done when:** a scoped run lints the diff and says what it did not lint.

### Task 6: licence compliance and SBOM

**Purpose:** two checklist lines with nothing behind them. `pip_audit` covers
vulnerabilities; no licence is ever checked and no SBOM is produced.

**Files:**
- Create: `tools/deps.py` — `licences()`, `sbom()`, `main()`
- Create: `tools/test_deps.py` — a forbidden licence fails; a missing tool is named
- Modify: `.claude/project-checks.json` — registers both in the slow tier

**Depends on:** none

**Implementation notes:**
- Read declared dependencies from `pyproject.toml` and resolve installed
  metadata via `importlib.metadata` — stdlib, no new dependency.
- **A denylist, not an allowlist**: strong-copyleft licences fail, unknown ones
  are *named as unknown* rather than passed. Article V.
- SBOM in CycloneDX-shaped JSON, written to a path the release candidate reads.
- A tool that is not installed is skipped and named, never failed.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_deps.py`
- Expect: exit 0, including a case where an injected GPL dependency fails and one
  where an unresolvable licence reports `unknown` rather than passing

**Done when:** a forbidden licence blocks, an unknown one is named, and an SBOM
file exists with every declared dependency in it.

### Task 7: the release candidate, with rollback executed

**Purpose:** §12's staging report is what Gate 2 is supposed to review, and it
has never existed — which is why Gate 2 has never had anything to show.

**Files:**
- Create: `tools/release_candidate.py` — orchestrates the rehearsal and emits the report
- Create: `tools/test_release_candidate.py` — the report names every fact
- Modify: `.claude/skills/releasing/SKILL.md` — Gate 2 reads the report

**Depends on:** 2, 6

**Implementation notes:**
- **Reuse `tools/test_package.py`'s rehearsal.** An `ISSUES.md` entry records two
  hooks already shelling out to `install.py` with near-identical logic; a third
  caller is the same defect. Import or invoke it, do not reimplement.
- The report carries: the wheel's version and hash, the target repo's own tier
  result, the SBOM path, the licence verdict, the risk tier, the changed-path
  count, and **the rollback result**.
- **Rollback is executed, not described.** After the install proves green, run
  `install.py --uninstall` in the same scratch repo and assert the layer is gone
  and the preserved files survive. The checklist is explicit that a documented
  rollback does not count.
- Any fact it could not establish is printed as `unknown`, and the exit code
  distinguishes that from ready.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_release_candidate.py`
- Expect: exit 0, with a case asserting the report contains a rollback result
  that came from a real uninstall, and one proving an undetermined fact exits
  non-zero rather than reporting ready

**Done when:** Gate 2 has a report to review, and the rollback line in it is the
output of a rollback that ran.

### Task 8: rollback and preconditions in the task shape

**Purpose:** the checklist wants every plan step to carry a rollback strategy and
to halt if its preconditions no longer hold. Neither is part of the task shape.

**Files:**
- Modify: `.claude/skills/writing-plans/references/task-decomposition.md` — two new fields
- Modify: `tools/analyze.py` — requires them
- Modify: `tools/test_analyze.py` — the fixture gains them

**Depends on:** none

**Implementation notes:**
- `**Rollback:**` and `**Preconditions:**` per task. Keep both short — a field
  nobody can fill in one line becomes boilerplate, and boilerplate is worse than
  absence because it reads as considered.
- `analyze.py` requires them **per task**, not per plan, so a single global line
  cannot satisfy every task.
- This plan predates the fields; it is exempt and says so under Complexity
  tracking rather than being retrofitted mid-flight.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_analyze.py`
- Expect: exit 0, with a case proving a task missing either field is a finding

**Done when:** a plan whose task omits a rollback cannot pass `analyze.py`.

### Task 9: git operations

**Purpose:** `git rebase` appears in zero layer files, `--force-with-lease` in
zero, conflict classification is prose, and PR bodies come from `gh pr create
--fill` rather than from the plan.

**Files:**
- Create: `tools/git_ops.py` — `rebase_plan()`, `classify_conflict()`, `pr_body()`
- Create: `tools/test_git_ops.py` — each against a real temp repo
- Modify: `.claude/skills/delivering/SKILL.md` — reads it

**Depends on:** none

**Implementation notes:**
- **It reports and composes; it does not push.** `rebase_plan()` returns what a
  rebase would do; `pr_body()` returns text. `test_process_router.py` already
  fails any file acquiring `gh pr merge` and this one is in its scan.
- `classify_conflict()` is mechanical-vs-substantive from the conflicting paths
  and hunks: a lockfile or a generated file is mechanical, anything under an auth
  or migration path is substantive and escalates. Reuse the existing tables.
- `pr_body()` composes from the plan's Goal, its ticked tasks, the risk tier and
  the review findings — never from the raw commit list, which is `wip:` noise.
- Real temp repos with a genuine conflict, torn down in a `finally`.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_git_ops.py`
- Expect: exit 0, including a real two-branch conflict classified both ways and a
  PR body containing the plan's goal and the tier

**Done when:** a conflict is classified by a mechanism, and a PR body is composed
from the plan rather than the commits.

### Task 10: a per-unit budget ceiling

**Purpose:** the checklist asks for a budget ceiling per run that escalates
rather than running unbounded. Nothing bounds a run.

**Files:**
- Create: `tools/budget.py` — `spent()`, `verdict()`, `main()`
- Create: `tools/test_budget.py` — the ceiling escalates rather than blocking

**Depends on:** 2

**Implementation notes:**
- **Tokens are not observable from here, so they are not the unit.** The ledger
  records one entry per turn with a timestamp, so *turns in a unit* and *elapsed
  wall time* are both measurable and honest. Counting a proxy and calling it
  tokens would be the defect this whole plan is closing.

  **Resolved at Gate 1 — turns and elapsed are the unit.** The module must say
  in its own docstring that this is *not* a token budget and that token spend is
  not observable from here, so nobody later reads the number as cost. The
  alternative considered was dropping the task and recording §cost-governance as
  absent; measuring what is measurable beats recording nothing, provided the
  limitation is stated where the number is printed rather than in a plan nobody
  re-reads.
- It **reports**; it never halts. Task 3's kill switch is the thing that halts,
  and a budget that halts on its own would stop a run mid-edit.
- Default ceiling stated in the module with how it was measured, as
  `VOLUME_LIMIT` and `BREADTH_WORDS` already are.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_budget.py`
- Expect: exit 0, with a case where a ledger past the ceiling reports escalation
  and one where an empty ledger reports `unknown` rather than `within budget`

**Done when:** a unit past its ceiling says so with a number, and an unmeasurable
one is named rather than passed.

### Task 11: Gate 1 is reachable, and the claim about plan mode is corrected

**Purpose:** a defect shipped earlier today. Gate 1 was changed to
`ExitPlanMode`, and that tool **refuses outside plan mode**:

    You are not in plan mode. To enter plan mode, call the EnterPlanMode tool first.

Since the same change removed `AskUserQuestion` from `writing-plans` and added an
assertion forbidding it, **Gate 1 currently has no working mechanism unless the
session already happened to be in plan mode.** The chain's first gate is
conditional on something no skill controls.

Worse, `references/plan-mode.md` states *"There is no tool for it"* about entering
plan mode. `EnterPlanMode` exists — the refusal message names it. That is a
document asserting a capability limit that is not real, which is the defect class
this repository names most often, committed by the file written to explain the
gate.

**Files:**
- Modify: `.claude/skills/writing-plans/references/plan-mode.md` — the corrected claim and the reachability rule
- Modify: `.claude/skills/writing-plans/SKILL.md` — how Gate 1 is reached
- Modify: `tools/test_process_router.py` — assert reachability, not just presence

**Depends on:** none

**Resolved by the user mid-plan: the skill enters plan mode itself.** "The agent
have to switch to PLAN mode automatically. Not me manually selecting."

**Implementation notes:**
- **`writing-plans` calls `EnterPlanMode` at the start of Stage C**, before it
  reads the repository to plan. The agent initiates; the tool's own contract says
  it *"REQUIRES user approval — they must consent to entering plan mode"*, so the
  user consents to a prompt rather than having to remember to select a mode. That
  is what makes it automatic without taking the choice away.
- Delete the false sentence in `plan-mode.md`. What is true: `EnterPlanMode` and
  `ExitPlanMode` both exist, `ExitPlanMode` refuses unless plan mode is active,
  and no tool sets the mode without the user's consent.
- **The blanket "never `AskUserQuestion`" assertion is wrong and must be
  narrowed.** `EnterPlanMode`'s documentation says outright: *"Use
  `AskUserQuestion` if you need to clarify approaches"* inside plan mode, and
  *"Do NOT use `AskUserQuestion` to ask 'Is this plan okay?'"*. The rule is
  therefore about the **approval**, not about the tool: Gate 1's approval is
  `ExitPlanMode` and only `ExitPlanMode`; a clarification inside plan mode may
  use `AskUserQuestion`. Today's assertion forbade both and was over-tight.
- The current assertion checks that the marker *has its tool named in the file*.
  That is presence, not reachability, and it passed while the gate was
  unreachable. Assert reachability: the skill must name `EnterPlanMode` as the way
  it gets into plan mode, and must not use `AskUserQuestion` for the approval
  itself.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0, with assertions that `writing-plans` names `EnterPlanMode`,
  that Gate 1's approval is `ExitPlanMode`, and that no `AskUserQuestion` sits on
  the approval line — the narrowed rule, not the blanket one

**Done when:** the skill enters plan mode on its own initiative, Gate 1 is asked
with `ExitPlanMode` from any starting mode, and no file claims a tool does not
exist when it does.

### Task 12: contracts and policy

**Purpose:** every rule this plan adds gets an assertion, and the policy files
describe what was built rather than what was intended.

**Files:**
- Modify: `tools/test_process_router.py` — every contract above
- Modify: `.claude/skills/knowledge-manager/formats.md` — recurring-findings capture
- Modify: `.claude/settings.json`, `.claude/hooks/hooks_registry.json` — the two new hooks
- Modify: `.claude/project-checks.json` — the new suites
- Modify: `.claude/workflow.md`, `CLAUDE.md`, `README.md` — policy
- Modify: `GOAL_CHECKLIST.md` — tracked, so the brief ships with the work

**Depends on:** 3, 4, 5, 6, 7, 8, 9, 10, 11

**Implementation notes:**
- Prose last, so it describes the mechanism rather than predicting it. This
  repository's most-repeated defect is a document asserting what the wiring does
  not do, and it recurred twice today.
- Assert: the halt guard denies; every writing agent declares a path scope; the
  release report carries an executed rollback; a task without a rollback fails
  `analyze.py`; nothing acquired `gh pr merge`.
- Re-run the audit against `GOAL_CHECKLIST.md` and update the artifact, so the
  counts in it describe the tree after this plan rather than before it.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS` with the suite count, and no check reported as skipped

**Done when:** the full tier is green and every rule above has an assertion
behind it.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Tasks 1, 2, 3, 4, 6, 8, 9, 10, 11 write the case before the change
- [x] III Smallest change — six new tools; every other change edits a file that already owns the concern
- [x] IV Reversibility — nothing pushes, merges or deploys; Task 7's rollback is exercised in a scratch repo and torn down
- [x] V No silent degradation — an unknown licence is named, an unestablished release fact exits non-zero, an unmeasurable budget reports unknown, an unscoped agent write is denied
- [x] VI Mechanism — Task 11 is the point: every rule here gets an assertion
- [x] VII Secrets — no credential enters the repo; the halt flag is machine-local and ignored

## Complexity tracking

No unticked boxes. One stated exemption: **this plan predates Task 8's
`**Rollback:**` and `**Preconditions:**` fields and does not carry them.**
Retrofitting them mid-flight would mean editing an approved plan's every task,
which is the churn the fields exist to avoid; Task 8 applies to the next plan
written.

## Risks

- **Task 4 may not be enforceable.** The guard needs the dispatched agent's
  declared file set at the moment of the write, and a subagent's environment may
  not carry it. If it cannot be established the guard denies, which is safe but
  could block legitimate work — if that proves unworkable the honest outcome is
  to record that file scope stays prompt-level and delete the claim, exactly as
  Task 3 of the previous plan was written to allow.
- **Task 7 is the longest-running thing here.** It builds a wheel and creates two
  virtualenvs, so it belongs in the slow tier and must never gate an auto-commit.
- **Task 10 rests on an open question**, marked inline. If a turn-and-elapsed
  ceiling is not an acceptable proxy, that task narrows to reporting only.
- **Twelve tasks is a large unit.** The Terraform argument applies — approve the
  graph, not the nodes — and `parallel_groups.py` will schedule it. Tasks 5, 6, 8
  and 9 are independent of everything and can land in any order.
- **Two hooks are added to a per-turn event.** Hook runtime is a correctness
  property here: one shipped at 5.2s this morning because nothing measured it.
  Both new hooks need an elapsed assertion.

## Out of Scope — and why, rather than prose that pretends otherwise

These `GOAL_CHECKLIST.md` lines have **no honest implementation in this
repository**, and writing skills that describe them would reproduce the exact
defect the audit measured — a document asserting a capability the wiring does not
have:

| Line | Why it is out |
|---|---|
| §13 progressive rollout, canary percentages | There is no running service to roll out to. The wheel either installs or does not |
| §13/§14 automatic rollback on error rate, latency, saturation | No production metrics exist, because nothing is serving traffic |
| §14 alerting, on-call dashboards, bake time per tier | Same: no deployed system to observe |
| §9 DAST against a staging instance | No HTTP surface to test |
| Gate 2 auto-approve for low-risk plans | **Refused on purpose.** A tier computed by the system that wants to ship must not waive the one rule with no exceptions. Already asserted |
| Feature-flag / canary wiring validation | No flags, and inventing them to validate them is circular |

Also out: pushing, merging, or opening a PR for `feat/target-workflow` — the user
chose to keep it local, and delivery is its own decision.

**If this repository ever grows a served surface, these become real and get their
own plan.** Recording them as out-of-scope with a reason is the point: the next
reader can tell "we decided not to" from "we forgot".

## Approved

2026-08-10. Gate 1 passed. Budget unit resolved as turns and elapsed, with the
token gap to be stated in `budget.py`'s own docstring. Execution runs with
fan-out: round 1 dispatches six `task-implementer` agents concurrently, per
`tools/parallel_groups.py`.

**Gate 1 was asked with `AskUserQuestion`, not `ExitPlanMode`, because
`ExitPlanMode` refuses outside plan mode and this session was not in it.** That
is the defect Task 11 fixes, and it is recorded here rather than smoothed over:
the gate mechanism shipped this morning is conditional on a mode nothing enters,
and it passed its own assertion because the assertion checked for the tool's
name in the file rather than for the gate being reachable.

Two corrections to today's work came out of reading the tools' actual contracts,
and Task 11 carries both: `plan-mode.md` claims `EnterPlanMode` does not exist,
and the "never `AskUserQuestion`" assertion is over-tight — the official guidance
permits it for clarification *inside* plan mode and forbids it only for the
approval. The user's instruction settled the remaining choice: the skill enters
plan mode itself rather than waiting to be put there.
