# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

Two units shipped on 2026-08-10/11, both closing gaps in the layer itself: the
target-workflow architecture, then twelve tasks against `GOAL_CHECKLIST.md`.
See `LOG.md` for both.

**Parallel subagent dispatch works, six at a time.** This file once said *"No
subagent has ever completed a task."* That is now two records out of date.

<!-- session-context:start -->

## Current Work

Branch `feat/checklist-completion`, **17 commits ahead of `main`**
(`c9f7ce6..198b559`), `63 files changed, 9175 insertions(+), 508 deletions(-)`.
**Nothing is pushed and no PR is open** — kept local by explicit choice.

The unit is complete through the chain: 12/12 tasks ticked with quoted
verifications, `verifying-work` returned **gaps** (named below), `no-slop`
swept repo-wide and applied no local repairs, `code-review` returned
**`passed: true`** with three P2 findings. Full tier at close:
`PASS: 49 check(s) green (audit, build, lint, smoke, test, typecheck)`.

Nine new tools: `chain.py`, `memory.py`, `worktree.py`, `halt.py`, `deps.py`,
`git_ops.py`, `release_candidate.py`, `budget.py`, plus risk tiering in
`scope.py`. Two hooks now fire every turn: `pre-run/01-halt-guard.py` and
`pre-edit/02-agent-scope-guard.py`.

## Pending

Four follow-ups, all identified by the chain itself rather than by a person.
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

5. **`WAITING_DELIVERY` never fires.** `derive_state` returns `BUILD` on
   `checks_green is None`, before reaching it — and `checks_green` comes from
   `refs/uaios/green/<slug>`, which only the auto-commit hook writes. Commit by
   hand, or have the auto-commit refuse once, and the ref is never set: this
   branch has no green ref while five older slugs do. The chain instrument then
   reports `stalled` forever on a finished unit, correctly by its own rule. See
   `ISSUES.md` 2026-08-11 21:45.

Unchanged and still true: branch protection is unavailable on this repo tier
(`403 Upgrade to GitHub Pro`); seven branches merged into `main` are dead
weight; `feat/adaptive-workflow` @ `076914e` carries a superseded plan nothing
marks as superseded.

## Next Steps

1. Decide whether `feat/checklist-completion` is pushed. It is reviewed and
   green; `tools/delivery_check.py --base main --head feat/checklist-completion`
   should be run and quoted first, and pushing needs an explicit yes.
2. Take the four Pending items through `writing-plans` as one unit — they are
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

<!-- session-context:end -->
