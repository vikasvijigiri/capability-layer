# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

Six units on 2026-08-10/11/12, all closing gaps in the layer itself: the
target-workflow architecture, twelve tasks against `GOAL_CHECKLIST.md`, the
security gate, the `/skills-doctor` retirement, the chain fingerprint fix, and
the concurrent check tier. See `LOG.md` for each.

<!-- session-context:start -->

## Current Work — START HERE

**`feat/security-gate` holds ten commits, all local, none pushed, no PR.** Tree
clean apart from this record. Full tier: `PASS: 52 check(s) green (audit, build,
lint, smoke, test, typecheck)`.

    ee6e56d  Cap knowledge-doc entries with a check
    5e9eaf6  Halve the session preamble; fix the task pointer that never worked
    3974610  Move operating detail out of the preamble; size the pool to the box
    3421fbb  Guard the jobs config; stop restating a cost that went stale
    ...and six earlier, see LOG.md

`TASK.md`'s S1 is **done except by choice**: preamble 25,599 → 9,986 ch,
SessionStart 6,258 → 3,349, check tier 3.4x (68.2s → 20.2s interleaved).
`tools/bench.py --save` holds the baseline; compare with it, never with a
remembered number. **Four things remain and every one needs a decision, not
work** — see Next Steps.

**A delivery decision is owed on four units at once** — the branch stacks on
`feat/close-remaining-gaps`, whose own ten-task plan is approved and unstarted,
which in turn stacks on `feat/checklist-completion` (17 commits, reviewed,
green, undelivered). Three undelivered branches deep is still the real state.

**The gate is the thing to read first.** `python tools/security_gate.py --base
main` — five clauses, each a fact about the artefact, in the `audit` kind.
Read its docstring before changing it: the reason it is **not** a receipt is the
whole design, and `decisions/2026-08-12-escape-hatches-inherit-trust.md` records
the one time that design was nearly lost.

**Three findings bind later work:**

- **`WAIVABLE_CLAUSES` holds two of five.** `secret-in-branch`,
  `agent-unscoped` and `dependency-risk` cannot be waived by an inline allow;
  adding one to that tuple fails an existing test on purpose.
- **Skills that read the same surface state their boundary on both sides**, and
  `test_process_router.py` fails if either stops naming the other. Three pairs
  now: `no-slop`/`code-review`, `no-slop`/`capability-layer-maintenance`, and
  `code-review`/the security gate.
- **Do not trust an instrument you have not seen go red.** `chain.py`'s stall
  detector was two-limbed for its whole life while its documentation described
  three. See `ISSUES.md` 2026-08-12 01:10.

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

0. **Four optimisation items are blocked on a decision, none on work.**
   (a) Skill/command/agent descriptions are 12,732 ch injected *every turn* —
   the last big cost. Cutting them safely needs `tools/eval_triggers.py`, which
   is 180 `claude -p` calls per repeat; unattended spend needs a yes. Declined
   once on 2026-08-12, so the per-turn cost stands.
   (b) `CLAUDE.md` is 9,986 ch against a ≤5,000 target; what is left is the
   skills table and the repo map, and which of those to lose is a judgement
   about this repo, not a mechanical cut.
   (c) Wiring `--scoped` into the per-turn path is the largest remaining
   latency win and changes what a checkpoint *guarantees* — policy, not code.
   (d) Pending 10, the two routers.
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
8. **`.claude/workflow.md`'s three-limb stall rule is now true for the first
   time.** It was written to describe a fix that a random fingerprint had
   silently disabled; `f641681` makes the description accurate. Nothing needs
   editing — but if the detector is ever changed again, the property to preserve
   is that its fingerprint is stable ACROSS processes, and the test that proves
   it must use a hard-coded digest.
9. **A unit of this size gets no automatic recovery point.** The auto-commit
   refused every turn (past `DEFAULT_MAX_FILES = 25`), and uncommitted work was
   lost to a `git checkout --` with no checkpoint holding it. Either the size
   gate is wrong for planned multi-task units, or `/save` must be run at task
   boundaries rather than at the end.

### Added by the concurrent-check-tier unit

10. **The entry classifier and `workflow.md`'s small-work path disagree, and the
    disagreement favours the less careful route.** For `add a --jobs flag to
    run_checks.py` the classifier is silent ("a named file plus a concrete
    value"), while `scope.py` calls that same file a `control-surface`, risk
    `high` — which is what the small path's own condition vetoes on. This
    session's `_projectchecks.py` change was exactly that shape. Reconciling two
    routers is a decision, not a merge; it is the whole of S2 and is smaller
    than "build a router", because the classifier already discriminates.
11. **`resume.py` reported `BUILD` for 57 turns against a stale slug.** It keys
    state to `security-gate` from the branch name; that plan is complete and
    this unit never had one, so there was nothing to advance. Compounds Pending
    5 rather than duplicating it — that one is the green ref never being
    written, this one is the slug pointing at a finished unit. A unit worked
    without a plan is invisible to the chain, which is worth deciding about
    before the small-work path makes plan-less units routine.
12. **A check `timeout` bounds the verdict, not the wall clock.** `shell=True`
    kills the shell, the grandchild survives, `communicate()` blocks on the
    inherited pipe. A hung check blocks a turn for its full runtime whatever
    `timeout` says. `tools/smoke.py:57` already solved it with `taskkill /T`;
    `run_checks` does not use it. Open, with the fix known — `ISSUES.md`
    2026-08-12 08:40.

<!-- session-context:end -->
