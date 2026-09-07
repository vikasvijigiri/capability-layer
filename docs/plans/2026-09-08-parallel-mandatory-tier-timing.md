# Parallel execution mandatory + tier/sweep/review are delivery-only — Implementation Plan

**Slug:** parallel-mandatory-tier-timing

## Approved

Gate 1 passed 2026-09-08 on branch `feat/parallel-mandatory-tier-timing`
(off `main`). The compact-plan-format unit is a separate, committed unit on
`feat/compact-plan-tier` (`1e89924`).

## Context

Two policies in this layer are already written but stated as soft defaults, and
one file contradicts them. `operating.md`'s "### Subagents" paragraph still says
subagents run "**only when the user has asked for subagents**" and "`implementer`
**never runs two at once**" — directly against `workflow.md` §Parallelism
("branch per task is the default, not an aspiration") and
`implementation/SKILL.md:130` ("Concurrent dispatch is the default, not an
ask"). Separately, the full check tier, the refactoring sweep and the review
gate are meant to run **once per unit at delivery**, but nothing states that
emphatically, so they get run per-task and mid-chain (this session did exactly
that). Outcome: one consistent, mandatory story — parallel by default, heavy
gates once at the end.

- **Goal:** make concurrent implementer dispatch **required** for any schedulable multi-task round (serial is a defect, not a choice), and state that the full tier / refactoring sweep / code-review run once per unit at delivery — never per task, never mid-chain.
- **Constraints:** no `tools/` logic change; `test_process_router.py`, `test_workflow_contract.py`, `test_referenced_paths.py` stay green; two-gate rule untouched; no bare backticked lowercase word in `workflow.md` that reads as a skill name (`test_process_router.py` trap).
- **Input:** `.claude/operating.md` (stale "### Subagents" para + two-tier table), `.claude/workflow.md` §"Parallelism and integration" + §tiers, `.claude/skills/implementation/SKILL.md` (~line 84, ~line 130).
- **Output:** `operating.md` subagent para rewritten (parallel = default; user opt-**out**, not opt-in; keep the real constraints — disjoint files, frozen interfaces, verify each round); one line that `--tier all` is delivery-only, once; `workflow.md` §Parallelism says a schedulable concurrent round **must** dispatch concurrently and names the integration order; `implementation/SKILL.md` wording aligned to "required".
- **Done Checks:** `python tools/run_checks.py --tier all --require-test` exits 0, run **once** at delivery of this unit · `grep -c "only when the user has asked for subagents" .claude/operating.md` → 0 · `grep -c "never runs two at once" .claude/operating.md` → 0.
- **Out of Scope:** `tools/parallel_groups.py` / `worktree.py` / `loop.py` / auto-commit-gate logic; new hooks; `.claude/policies/*`; the compact-plan-format unit (separate, done, on `feat/compact-plan-tier`).

**Risk:** high — `python tools/scope.py --plan` forces high: `.claude/operating.md` and `.claude/workflow.md` are control surfaces (`tools/scope.py:68`). Prose-only change, no logic; Gate 2 still applies at shipment.

**Blast radius:** how every future multi-task plan is executed (concurrent vs serial) and when the slow tier / sweep / review fire. No runtime code, no test, no hook. Reversible by revert.

**Rollback:** revert the squash/merge commit — the three files return to today's wording. No state, no migration.

## Constitution gate
- [x] I Evidence — each task names a grep/suite command and its expected result
- [x] II Test first — prose-and-policy change; the guards are the existing `test_process_router.py` + `test_workflow_contract.py`, run per task
- [x] III Smallest change — three prose edits; no tool or test logic touched
- [x] IV Reversibility — single revert, no state
- [x] V No silent degradation — no check is removed or weakened; the change moves heavy checks to run once, not zero times
- [x] VI Mechanism — the parallel-default rule is already enforced by `parallel_groups.py` + `implementation/SKILL.md`; this removes a contradicting prose copy so the mechanism reads consistently
- [x] VII Secrets — none

## Complexity tracking
All boxes ticked. Per-task Rollback/Preconditions: every task edits one prose
file and is covered by the plan-level **Rollback**; not repeated per task.

## File map
- Modify: `.claude/operating.md` — rewrite "### Subagents"; add the "`--tier all` once, at delivery" line to the tiers section
- Modify: `.claude/workflow.md` — §"Parallelism and integration": soft default → required; add the integration-order sentence
- Modify: `.claude/skills/implementation/SKILL.md` — align dispatch + tier wording to "required / once at delivery"

## Progress
- [x] Task 1 [P] — operating.md: repair the stale subagent paragraph + tier-timing line
- [x] Task 2 [P] — workflow.md: parallel round is required + integration order
- [x] Task 3 [P] — implementation/SKILL.md: wording alignment

All three built by parallel `implementer` dispatch (worktree + branch each),
cherry-picked to this branch as `2faae61` / `321d881` / `c74586e`; sweep fix
`760eb6c`. `run_checks.py --tier all`: PASS 63. Delivered as PR #51 — awaiting
CI (GitHub Actions billing-blocked) and the merge decision.

## Tasks

### Task 1: operating.md — repair stale subagent paragraph + add tier-timing line
**Files:**
- Modify: `.claude/operating.md` — "### Subagents" paragraph and the two-tier checks section
**Depends on:** none
**Verification:**
- Run: `python tools/test_process_router.py` and `grep -n "asked for subagents\|never runs two at once\|delivery" .claude/operating.md`
- Expect: suite passes; the two stale phrases are gone; a line states `--tier all` runs once at delivery
**Done when:** `operating.md` says concurrent dispatch is the default (user opt-out), keeps the disjoint-files / frozen-interfaces / verify-each-round constraints, and states the slow tier is a once-per-unit delivery gate.

### Task 2: workflow.md — schedulable concurrent round must dispatch concurrently + integration order
**Files:**
- Modify: `.claude/workflow.md` — §"Parallelism and integration"
**Depends on:** none
**Verification:**
- Run: `python tools/test_process_router.py` and `python tools/test_workflow_contract.py`
- Expect: both pass (no new bare backticked lowercase token read as a skill name)
**Done when:** the section says serial execution of a schedulable concurrent round is a defect, and names the order: parallel tasks finish → resolve conflicts → testing → refactoring sweep → full tier → code-review → PR / merge.

### Task 3: implementation/SKILL.md — wording alignment
**Files:**
- Modify: `.claude/skills/implementation/SKILL.md` — the "Dispatching subagents" section and the `--scoped` / full-tier line (~line 84)
**Depends on:** none
**Verification:**
- Run: `python tools/test_process_router.py` and `python tools/test_referenced_paths.py`
- Expect: both pass
**Done when:** the skill says concurrent dispatch is required for a schedulable multi-task round, per-task verification is `--scoped` / targeted, and `--tier all` is the single delivery gate.

## Verification (end to end)

1. `python tools/analyze.py --slug parallel-mandatory-tier-timing` — plan consistent.
2. `python tools/parallel_groups.py <this plan>` — 3 tasks, one round, concurrency 3 (disjoint files).
3. Execute the round **concurrently** — a worktree + branch per task, `implementer` each, dispatched in one message — to demonstrate the rule being made mandatory. Merge the three branches, resolve any conflict.
4. `python tools/run_checks.py --tier all --require-test` — **once**, after the round — exits 0.
5. `grep` checks from **Done Checks** above.
