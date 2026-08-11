# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

Three units on 2026-08-10/11/12, all closing gaps in the layer itself: the
target-workflow architecture, twelve tasks against `GOAL_CHECKLIST.md`, then the
security gate. See `LOG.md` for all three.

<!-- session-context:start -->

## Current Work — START HERE

**The security gate is complete through review and sitting local on
`feat/security-gate`.** Two commits, `d654ee5` (the gate) and `4fece17` (the
repair review round 1 demanded), `21 files changed, 1748 insertions(+), 19
deletions(-)` against `feat/close-remaining-gaps`, which is where the branch was
cut from. Plan `docs/plans/2026-08-11-security-gate.md`, 8/8 tasks ticked. Full
tier: `PASS: 51 check(s) green (audit, build, lint, smoke, test, typecheck)`.
**Nothing pushed, no PR, and the branch stacks on a parent whose own ten-task
plan is unstarted.**

`python tools/security_gate.py --base main` is the new check. Five clauses, each
a fact about the artefact rather than about process, in the `audit` kind so it
gates push/PR and CI but not the per-turn auto-commit. Read its docstring before
touching it: the reason it is **not** a receipt is the whole design, and
`decisions/2026-08-12-escape-hatches-inherit-trust.md` records the one time that
design was nearly lost.

To resume: `python tools/resume.py`. The unit is recorded and needs no further
work — a delivery decision is owed, not a build.

**Two decisions from this unit are binding on later work:**

- **`WAIVABLE_CLAUSES` holds two of five, and `secret-in-branch` is not one of
  them.** Adding a clause to that tuple fails an existing test on purpose.
- **`no-slop` and `code-review` state their boundary on both sides**, and
  `test_process_router.py` fails if either stops naming the other. The audit's
  proposal to merge them was resolved at Gate 1 to keep both.

## Previous Work

Branch `feat/close-remaining-gaps` — the parent — carries an approved, unstarted
ten-task plan (`docs/plans/2026-08-11-close-remaining-gaps.md`, risk `high`) and
26 commits inherited from `feat/checklist-completion`. Nothing there was touched
by this unit.

`feat/checklist-completion` remains 17 commits ahead of `main`, reviewed, green,
local, and undelivered.

## Pending

Five follow-ups, all identified by the chain itself rather than by a person.
Each is its own unit and enters at `writing-plans`:

1. **`pre-edit/02-agent-scope-guard.py` has no caller.** It denies correctly
   when `UAIOS_AGENT_NAME` is set, and **nothing sets it** — a grep finds the
   name only in the guard and its test. On a real dispatch the hook runs and is
   silent, so agent file scope is enforced in principle and not in practice.
   Either the dispatch sets it, or the claim narrows.
2. **The ticked-task checkbox is defined four times** — `analyze.PROGRESS_RE`,
   `chain.PROGRESS_TICK`, `git_ops`' own, `resume._CHECKBOX`. They already
   disagree: three require `Task <n>`, `resume`'s matches any box under
   `## Progress`. Needs an owner chosen; `resume`'s looser match may be
   deliberate, so this is not a mechanical merge.
3. **`budget.ELAPSED_CEILING_HOURS = 3.0` is wrong.** The first complete unit
   it measured came in at 19.93h — 6.6× over. It was calibrated on two
   *left-censored* samples, so it encoded how much of a unit happened to be
   visible rather than how long one takes. Re-measure from complete units, or
   drop the elapsed limb and keep turns.
4. **`ISSUES.md` carries two `0x08` bytes**, in the entry describing `0x08`
   bytes. See `ISSUES.md` 2026-08-11 21:15.

5. **`refs/uaios/green/` has one writer, and it is the auto-commit hook.**
   Commit by hand — or have the auto-commit refuse once, which the minimal-diff
   gate is built to do — and the ref is never set, so `checks_green` stays
   `None` and `derive_state` returns `BUILD` before it can reach
   `WAITING_DELIVERY`. Setting the ref by hand on a verified tree resolved it
   immediately, so the state machine is sound and the plumbing is not. See
   `ISSUES.md` 2026-08-11 21:45.

Unchanged and still true: branch protection is unavailable on this repo tier
(`403 Upgrade to GitHub Pro`); seven branches merged into `main` are dead
weight; `feat/adaptive-workflow` @ `076914e` carries a superseded plan nothing
marks as superseded.

## Next Steps

1. Decide whether `feat/checklist-completion` is pushed. It is reviewed and
   green; `tools/delivery_check.py --base main --head feat/checklist-completion`
   should be run and quoted first, and pushing needs an explicit yes.
2. Take the five Pending items through `writing-plans` as one unit — they are
   small, related, and all concern mechanisms whose claims currently exceed
   their wiring.
3. `GOAL_CHECKLIST.md` is still untracked at the repo root. It is the brief for
   both audits; commit it or declare it.

## Open Questions

- **Is the Gate 1 → Gate 2 span autonomous?** No, and it cannot be made so by a
  hook — a hook may not invoke a skill. `chain.py` makes a missed handoff loud
  instead of silent, which is the ceiling. Whether an external driver
  (`tools/drive.py`) is worth building should be decided from the ledger it now
  writes, not from argument. The ledger has been accumulating since 2026-08-10.
- **What of the checklist cannot be built here?** 17 of 21 remaining absences
  need a running service — canary rollout, auto-rollback on error rate,
  alerting, bake time, DAST. This repository ships a wheel. They are recorded in
  the plan's Out of Scope *with reasons*, so a later reader can tell "we decided
  not to" from "we forgot". If a served surface ever appears, they become real
  and get their own plan.
- **Two audits are published and one is already wrong.** The second
  (`claude.ai/code/artifact/789942aa-667f-443e-8910-661568f3aa4d`) says 38
  mechanism; `verifying-work` found agent file scope overstated, so it is 37.
  The artifact has not been corrected.


### Added by the security-gate unit

6. **Two clauses have never fired on an organic branch.** `secret-in-branch` and
   `dependency-risk` are proven in fixtures and, for the first, by a deliberate
   injection that was then reverted. Neither has caught anything real, so
   neither is evidence of anything yet.
7. **The "five state reporters" question is open, and the obvious answer is
   wrong.** `/wip`, `/git-state`, `/handoff`, `tools/resume.py` and
   `session-start/03-state-report.py` overlap in *description*. Folding
   `/git-state` into `/wip` was planned, attempted and reverted — the bodies do
   not overlap. Whether anything should merge needs its own unit.
8. **A unit of this size gets no automatic recovery point.** The auto-commit
   refused every turn (past `MAX_FILES = 25`), and uncommitted work was lost to
   a `git checkout --` with no checkpoint holding it. Either the size gate is
   wrong for planned multi-task units, or `/save` must be run at task
   boundaries rather than at the end.

<!-- session-context:end -->
