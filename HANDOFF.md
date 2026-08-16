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

**`feat/security-gate` holds nineteen commits, all local, none pushed, no PR.**
Tree clean apart from this record. Full tier: `PASS: 52 check(s) green (audit, build,
lint, smoke, test, typecheck)`.

    cd43a20  Stop the layer breaking every host's test runner
    c4653f5  Add the direct-answer level; count calls objectives 4/5 need
    2a93290  Make commands user-only; merge the two post-tool hooks
    7f1f942  Route the small-work path; build the anti-repetition layer
    e136ec0  Delete CLAUDE.md's copy of the stage table
    ...and twelve earlier, see LOG.md

`TASK.md`'s S1 is **closed**: `CLAUDE.md`+rules 25,599 → 9,056 ch, SessionStart
6,258 → 3,349, check tier 3.4x (68.2s → 20.2s interleaved). All four
optimisation questions are answered in Next Steps 0 — three settled, one open
on evidence. `tools/bench.py --save` holds the baseline; compare against it,
never against a remembered number. **The largest remaining cost is the
17,900-char per-turn listing**, deliberately unpaid down — see 0(a).

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

**Portability was the worst defect and is fixed (2026-08-16, `cd43a20`): the
layer no longer ships its internal suites, and a fresh install is green in a
Python and a Node host. Verdict on the rest below.**

**The Notion Primary Objectives, audited fairly on 2026-08-15: 4 green,
3 amber, 3 red.** Two grades in the previous audit were generous and are
corrected: objective 4 was called green while nothing counted tool calls
(unmeasurable, not passing), and objective 8 was called green at 13% router
coverage. Equally, calling objective 8's 86% silence a gap was unfair —
30% are prompts a later stage's own description owns, which is the
documented mechanism working.

**Objective 2 is the one that matters and is untouched.** Per-turn cost is
4,475 tok against 3,172 fixed — 141x — and still +41% above where the
session began, because the skill rewrite added 6,674 chars. Whether that
stays or reverts depends entirely on the manual triggering test; every other
lever there is small change. Objectives 4 and 5 are now *measurable* but not
yet *measured in the wild*: the counter has seen only synthetic firings, and
the state file resets per session.

0. **All four optimisation items are now answered; one is open on purpose.**
   (a) **Descriptions: do not cut.** Approved on 2026-08-14 and stopped after
   $3.61. `eval_triggers.py` had never run live; once fixed it showed a query
   costs ~$0.45, so the approved run is **~$81**, and `code-review` measured
   trigger_rate 0.0 — a probe of "review this diff before I merge it" produced
   twelve Bash calls and no skill invocation. **This is the open item**: either
   `code-review` genuinely under-triggers, which the docs say is fixed by
   making the description *more* specific, or the harness still cannot see an
   invocation. Both need the same next step; spend the $81 there, not on
   shrinking. 12,732 ch/turn stands until it is settled.
   (b) **Done.** `CLAUDE.md`+rules 9,986 → 9,056 ch. The ≤5,000 target was
   abandoned deliberately: reaching it meant deleting the command list and
   repo map to save ~1,000 tokens once per session.
   (c) **Declined** on 2026-08-14 — `--scoped` stays off the per-turn path.
   (d) **Answered from the docs.** Routing is description-driven invocation
   plus `disable-model-invocation: true` for side-effecting skills. This layer
   sets `delivering` and `releasing` to `false` on purpose so the chain can
   hand off; Pending 10's entry-classifier is the part with no basis in the
   documentation.
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
