# Close the remaining GOAL_CHECKLIST gaps

**Goal:** close every remaining `GOAL_CHECKLIST.md` gap that has an honest
implementation here, and prove the deploy stages against a repo that has a real
surface rather than simulating them in one that does not.

**Slug:** close-remaining-gaps

**Risk:** to be filled by `python tools/scope.py --plan docs/plans/2026-08-11-close-remaining-gaps.md`

**Source brief:** `GOAL_CHECKLIST.md`, and the audit at
`https://claude.ai/code/artifact/789942aa-667f-443e-8910-661568f3aa4d`
(37 mechanism / 16 partial / 2 prose / 21 absent).


## Context

Two audits measured this layer against `GOAL_CHECKLIST.md`. The second reports
**37 mechanism · 16 partial · 2 prose-only · 21 absent** out of 77 checkable
lines. The distinction that matters throughout is *enforced by a mechanism*
versus *described in prose* — prose passes every test suite, which is why the
two are counted separately.

This plan closes the buildable remainder. Two decisions taken at the gate shape
it, and both narrow the scope rather than widening it:

**The deploy stages are proven against a separate repo, not built here.**
Seventeen absences need a running service — canary rollout, auto-rollback on
error rate, alerting, bake time, DAST, production-like load. `CLAUDE.md` states
*"There is no application code here."* Adding a demo app to satisfy a checklist
would contradict the repo's identity and produce simulated evidence. Instead
they are exercised against a product repo that has a real surface
(`../physrun`), and recorded as **proven elsewhere** with the command and its
output — which is what the checklist actually asks for.

**`**Preconditions:**` becomes a condition, not prose.** Today it is free text,
`analyze.py` checks only that the label exists, and no executed plan has ever
carried one. The single real example — *"`src/checkout.ts:submit` still makes
exactly one network call"* — is a semantic claim no fact can settle. Terraform's
`precondition` block (a `condition` expression plus an `error_message`, evaluated
before the resource is built, failing the plan rather than warning) and Ansible's
`assert` (conditions that must all hold, execution stops, message explains) agree
on the shape. This repo already has that vocabulary as `Run:` / `Expect:`, and
reusing it means no third plan parser.

## Approach

Ten tasks. Every one ends with a command that can fail.

### 1. `**Preconditions:**` becomes checkable

- `.claude/skills/writing-plans/references/task-decomposition.md` — the field
  becomes `Run:` + `Expect:`, the same shape `Verification` already uses.
- `tools/analyze.py` — require the *shape*, not just the label. A task whose
  precondition names no command is a finding, exactly as a missing
  `Verification` command already is.
- Reuse `parallel_groups.field()` (`tools/parallel_groups.py:135`) to extract
  the value. It already pulls inline-or-bulleted `**Key:**` values for
  `Files:` and `Depends on:`; `analyze.py`'s own `TASK_RE` + manual body-slicing
  extracts nothing and must not become a third parser.

### 2. `tools/preconditions.py` — evaluate them before a task runs

House shape, matching `delivery_check.py` / `scope.py` / `release_candidate.py`
exactly: `gather_facts(root, plan, offline=False) -> dict` feeding a pure
`evaluate(facts) -> list[dict]`, with `exit_code()` returning **2 for unknown**,
which is not 0. Tasks come from `parallel_groups.parse_plan()`.

**It reports; it does not halt.** `tools/halt.py` is the only thing that stops
work, and the caller decides — the house rule stated in all three existing
evaluators. A precondition whose command cannot run is `unknown`, never a pass.

### 3. Give `pre-edit/02-agent-scope-guard.py` a caller

It denies correctly and **nothing sets `UAIOS_AGENT_NAME`/`UAIOS_AGENT_SCOPE`**,
so agent file scope is enforced in principle and not in practice. Either the
dispatch sets them, or `parallel-dispatch.md` narrows the claim and the audit
verdict drops to `partial` honestly. Decide by trying the first.

### 4. One owner for the ticked-task pattern

Four definitions exist and already disagree: `analyze.PROGRESS_RE`,
`chain.PROGRESS_TICK`, `git_ops`' own, `resume._CHECKBOX` — three require
`Task <n>`, `resume`'s matches any box under `## Progress`. Pick `analyze.py` as
owner; import elsewhere. Where `resume`'s looser match is deliberate, say so at
the call site rather than silently keeping a fifth behaviour.

### 5. `refs/uaios/green/` gets a second writer

Only the auto-commit hook writes it, so a hand-made commit — or one refusal from
the minimal-diff gate, which is designed to refuse — leaves `checks_green` at
`None` forever, and `derive_state` returns `BUILD` before it can reach
`WAITING_DELIVERY`. Add `tools/run_checks.py --record-green` (or equivalent) so
a verified tree can record that fact through the mechanism that owns it.

### 6. Re-measure the budget ceiling

`budget.ELAPSED_CEILING_HOURS = 3.0` was derived from two *left-censored*
samples and the first complete unit came in at **19.93h**, 6.6× over. Re-measure
from finished units in the ledger, or drop the elapsed limb and keep turns.
State the censoring where the number is defined.

### 7. Scaffolding: `.claude/README.md`, `.claude/memory/`, `.claude/audit/`

`.claude/audit/` should point at the existing append-only ledger
(`.claude/hooks/state/chain-ledger.jsonl`) rather than become a second audit
trail — two would drift, and the ledger is the one with a suite.

### 8. Plan-level rollback, blast radius, minimality

Three `partial` lines that are each one field: a plan-level `**Rollback:**`
(Gate 1 is meant to show one; only per-task exists), blast radius captured at
intake as the sixth field `§1` asks for, and a minimality note on a
decomposition. All three enforced by `analyze.py`, not by instruction.

### 9. Changelog and semver from the plan

`git_ops.pr_body()` already composes from a plan's Goal, ticked tasks, tier and
findings. Extend the same function rather than writing a second composer.

### 10. Prove the deploy stages against `../physrun`

Run `releasing` end to end against a repo with a real surface, and record the
result — command and output — as evidence for §12–§14. This is the first time
Gate 2 will have been exercised at all. Where a stage still cannot be proven
there either, say which and why.

Also here: fix the two `0x08` bytes in `ISSUES.md`, and correct the published
audit from 38 to 37 mechanism.

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `tools/analyze.py` | Modify | Requires a precondition's *shape*, plus plan-level rollback, blast radius, minimality |
| `tools/preconditions.py` | Create | Evaluates a task's preconditions before it runs; reports, never halts |
| `tools/test_preconditions.py` | Create | An unrunnable precondition is `unknown`, never a pass |
| `tools/chain.py` | Modify | Imports the ticked-task pattern rather than defining it |
| `tools/git_ops.py` | Modify | Same import; composes a changelog and a version bump from the plan |
| `tools/run_checks.py` | Modify | `--record-green` so a verified tree can record that fact |
| `tools/budget.py` | Modify | A ceiling measured from finished units, with the censoring stated |
| `.claude/README.md` | Create | What the pipeline is, for a contributor who has read nothing else |
| `.claude/workflow.md` | Modify | Points `.claude/audit/` at the existing ledger rather than a second trail |
| `.claude/skills/writing-plans/**` | Modify | The task shape, the plan shape, and the three new plan-level fields |
| `.claude/skills/executing-plans/references/parallel-dispatch.md` | Modify | The agent scope claim matches the wiring |
| `.claude/skills/releasing/SKILL.md` | Modify | Records what was proven against a serving target |
| `.claude/project-checks.json` | Modify | Registers the new suite |
| `tools/test_*.py` | Modify | One case per rule added above, each red first |

## Progress

- [ ] Task 1 — `**Preconditions:**` becomes a checkable condition
- [ ] Task 2 — `tools/preconditions.py`, evaluating them before a task runs
- [ ] Task 3 — a caller for the agent scope guard, or a narrowed claim
- [ ] Task 4 — one owner for the ticked-task pattern
- [ ] Task 5 — a second writer for `refs/uaios/green/`
- [ ] Task 6 — re-measure the budget ceiling
- [ ] Task 7 — scaffolding: README, memory, audit pointer
- [ ] Task 8 — plan-level rollback, blast radius, minimality
- [ ] Task 9 — changelog and semver from the plan
- [ ] Task 10 — prove the deploy stages against `../physrun`

## Tasks

The design above is the argument for each; these blocks are what
`parallel_groups.py` schedules and what `executing-plans` ticks.

### Task 1: `**Preconditions:**` becomes a checkable condition

**Files:**
- Modify: `.claude/skills/writing-plans/references/task-decomposition.md`
- Modify: `tools/analyze.py`
- Modify: `tools/test_analyze.py`

**Depends on:** none

**Rollback:** revert the commit; the field returns to prose and no plan yet
carries one, so nothing downstream breaks.

**Preconditions:**
- Run: `python tools/analyze.py --slug close-remaining-gaps`
- Expect: exit 0 — the checker works before it is changed

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_analyze.py`
- Expect: exit 0, with a case proving a precondition naming no command is a
  finding, and one proving a well-formed `Run:`/`Expect:` pair is not

**Done when:** a task whose precondition is prose fails `analyze.py`.

### Task 2: `tools/preconditions.py`

**Files:**
- Create: `tools/preconditions.py`
- Create: `tools/test_preconditions.py`
- Modify: `.claude/project-checks.json`

**Depends on:** 1

**Rollback:** delete both files and the registration; nothing imports them.

**Preconditions:**
- Run: `python tools/parallel_groups.py docs/plans/2026-08-11-close-remaining-gaps.md`
- Expect: exit 0 — the per-task walker this reuses can read this plan

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_preconditions.py`
- Expect: exit 0, including a case where a precondition command cannot run and
  is reported `unknown` with exit 2, never as a pass

**Done when:** a stale precondition is reported before its task runs, and an
unrunnable one is named rather than counted green.

### Task 3: a caller for the agent scope guard

**Files:**
- Modify: `.claude/skills/executing-plans/references/parallel-dispatch.md`
- Modify: `tools/test_agent_standards.py`

**Depends on:** none

**Rollback:** revert; the guard returns to enforcing nothing, which is today.

**Preconditions:**
- Run: `python tools/test_agent_standards.py`
- Expect: exit 0 — the suite is green before the claim is changed

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_agent_standards.py`
- Expect: exit 0, asserting either that the dispatch sets the scope variables,
  or that no document claims file scope is enforced when it is not

**Done when:** the claim and the wiring agree, whichever way it resolves.

### Task 4: one owner for the ticked-task pattern

**Files:**
- Modify: `tools/chain.py`
- Modify: `tools/git_ops.py`
- Modify: `tools/test_process_router.py`

**Depends on:** none

**Rollback:** revert; four definitions return, which is today.

**Preconditions:**
- Run: `python tools/test_chain.py`
- Expect: exit 0 — the suite pinning the current pattern is green first

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_process_router.py`
- Expect: exit 0, with an assertion that one module defines the pattern

**Done when:** one definition exists and the others import it.

### Task 5: a second writer for the green ref

**Files:**
- Modify: `tools/run_checks.py`
- Modify: `tools/test_run_checks_scoped.py`

**Depends on:** none

**Rollback:** revert; the ref keeps its single writer.

**Preconditions:**
- Run: `git for-each-ref refs/uaios/green/`
- Expect: this branch's slug absent — the condition being fixed

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_run_checks_scoped.py`
- Expect: exit 0, with a case proving the ref is written only after a green run
  and never by a scoped one

**Done when:** a verified tree can record green without the auto-commit.

### Task 6: re-measure the budget ceiling

**Files:**
- Modify: `tools/budget.py`
- Modify: `tools/test_budget.py`

**Depends on:** none

**Rollback:** revert to the 3.0h ceiling.

**Preconditions:**
- Run: `python tools/chain.py --ledger`
- Expect: at least one complete unit present to measure from

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_budget.py`
- Expect: exit 0, and the module states how the number was measured and that
  the earlier samples were left-censored

**Done when:** the ceiling comes from finished units, or the elapsed limb is
gone.

### Task 7: scaffolding

**Files:**
- Create: `.claude/README.md`
- Modify: `.claude/workflow.md`

**Depends on:** none

**Rollback:** delete the file; the pointer reverts.

**Preconditions:**
- Run: `ls .claude/hooks/state/chain-ledger.jsonl`
- Expect: present — the audit pointer names it rather than duplicating it

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_referenced_paths.py`
- Expect: exit 0 — every path the new document names resolves

**Done when:** the audit trail has one owner and the README explains the
pipeline.

### Task 8: plan-level rollback, blast radius, minimality

**Files:**
- Modify: `.claude/skills/writing-plans/SKILL.md`
- Modify: `.claude/skills/writing-plans/references/plan-document.md`
- Modify: `tools/test_analyze.py`

**Depends on:** 1

**Rollback:** revert; the three fields become optional again.

**Preconditions:**
- Run: `python tools/test_analyze.py`
- Expect: exit 0 before the new requirements are added

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_analyze.py`
- Expect: exit 0, with a case per field proving its absence is a finding

**Done when:** Gate 1 can show a rollback and a blast radius because the plan
must carry them.

### Task 9: changelog and semver from the plan

**Files:**
- Modify: `tools/git_ops.py`
- Modify: `tools/test_git_ops.py`

**Depends on:** 4

**Rollback:** revert; `pr_body()` returns to its current output.

**Preconditions:**
- Run: `python tools/test_git_ops.py`
- Expect: exit 0 — the composer is green before it is extended

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_git_ops.py`
- Expect: exit 0, with a case proving the changelog comes from the plan and
  never from the raw commit list

**Done when:** a changelog and a version bump are composed from the plan.

### Task 10: prove the deploy stages against `../physrun`

**Files:**
- Modify: `.claude/skills/releasing/SKILL.md`

**Depends on:** 2, 5

**Rollback:** nothing deploys without Gate 2; the record is prose and reverts
with the commit.

**Preconditions:**
- Run: `ls ../physrun/pyproject.toml`
- Expect: present — the sibling repo exists and has a real surface. If absent,
  this task cannot run and must say so rather than simulate a result

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/release_candidate.py --plan docs/plans/2026-08-11-close-remaining-gaps.md`
- Expect: the report quoted in full, naming which stages were proven against a
  serving target and which could not be, with the command and output for each

**Done when:** §12-§14 are backed by evidence from a repo that actually serves
something, or are recorded as unprovable with the reason.

## Verification

Per task, its own command. For the unit:

```
python tools/run_checks.py --tier all --require-test     # expect PASS, nothing skipped
python tools/analyze.py --slug <slug>                    # expect: consistent, no findings
python tools/preconditions.py --plan <this plan>         # the new tool, on itself
python tools/memory.py --stale                           # expect exit 0
```

The honest end-state check is the re-audit: re-read all 77 lines against the
tree and publish the corrected counts. A number that goes up without a command
behind it is the thing this whole exercise exists to prevent.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Tasks 1, 2, 4, 5, 6, 8, 9 write the case before the change
- [x] III Smallest change — one new tool; every other task edits a file that
      already owns the concern
- [x] IV Reversibility — every task states a rollback; nothing pushes, merges or
      deploys without Gate 2
- [x] V No silent degradation — an unrunnable precondition is `unknown` with
      exit 2, and Task 10 records an unprovable stage rather than simulating it
- [x] VI Mechanism — every item closed here gets a test or a hook, which is the
      whole distinction the audit measures
- [x] VII Secrets — no credential enters the repo

## Complexity tracking

No unticked boxes. One stated exemption: this plan carries `**Preconditions:**`
in the `Run:`/`Expect:` shape Task 1 introduces, so it is written against a
contract that does not exist yet. That is deliberate — a plan that mandates a
field and does not use it is the prose-not-wiring defect this whole unit closes.

## Out of scope

- **Gate 2 auto-approve for low-risk plans** — refused on purpose, with an
  assertion. A tier computed by the system that wants to ship must not waive the
  one rule with no exceptions.
- **`state/intent.json`, `state/plan.json`** — refused by
  `decisions/2026-08-07-derived-state-over-stored-state.md`.
- **Adding an application to this repo** — decided at the gate; the deploy
  stages are proven elsewhere instead.
- **Merging PR #11** — that is a human's click.

## Approved

2026-08-11. Gate 1 passed via `ExitPlanMode` — the first approval that mechanism
has carried. Recorded in the ledger as
`gate 1: approve -- 10 tasks. Deploy stages proven against ../physrun rather
than built here; Preconditions become a condition following Terraform's
precondition shape.`

This heading is the exact string `tools/resume.py` derives state from. It was
first written as bold prose — **Approved** — and the unit read as
`WAITING_PLAN_APPROVAL` on a plan that had been approved. `writing-plans` warns
about precisely this, and the warning was still not enough: a paraphrase is
invisible to a parser.
