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

**PR #18 merged; `main` is at `247103e`.** Closed 2 of the 5 gaps from the
2026-08-16 audit (`docs/plans/2026-08-20-router-progress-consistency.md`),
bundled with 2 unrelated inherited commits from the prior
`skills/quality-audit-fixes` session (skill-content audit, portability work —
see `LOG.md` 2026-08-19). `python tools/run_checks.py --tier all
--require-test` on `main`: **`PASS: 54 check(s) green`**, verified fresh.

**The chain ran end to end for the first time this session.** `spec-reviewer`
and an independent `test-verifier` (red-green-proved, not just re-run) both
returned no findings; `no-slop` found and repaired 2 local issues; `code-review`
passed. The user merged PR #18 directly via GitHub rather than through
`releasing`'s `AskUserQuestion` — no deploy target exists, so that stage was
skipped per its own contract (confirmed with the user first). The shipment
decision is still recorded in the ledger: `python tools/chain.py --gate 2
--decision ship --reason "..."` was run retroactively against the actual
GitHub merge event, so the ledger's zero-gate-2-rows gap (noted below as an
Open Question for months) is now closed.

**Two Pending/Open-Questions items below are now closed by this unit** —
Pending #2 (the checkbox regex defined four ways) and Open Questions #10/#14
(the two routers disagreeing) — struck through in place rather than deleted,
per this file's own convention.

**Found during verification, not fixed:** `tools/resume.py`'s
`BRANCH_PREFIX = "feat/"` strips only one branch prefix, while
`.claude/hooks/_hooklib.py`'s `active_plans()` strips five
(`feat/`/`fix/`/`docs/`/`chore/`/`refactor/`) — confirmed unrelated to this
diff, but it meant `resume.py` could not resolve its own active plan by slug
for this entire session, since the branch was `fix/router-progress-consistency`.
See `TASK.md`'s Completed entry for the full trace. Worth its own small unit.

**Objective 2 (17,900 ch/turn) and objective 8's remaining router surface are
still open** — this unit closed the *specific reproduced case* HANDOFF named,
not the whole class. See Pending/Open Questions below, unchanged.

**`main`'s remote is `vikasvijigiri/capability-layer`.**

## Previous Work

The stack described in earlier revisions of this file
(`feat/close-remaining-gaps`, `feat/checklist-completion`) landed before this
session — see `TASK.md`'s Completed section for the full trail. Nothing from
that stack was touched by this unit.

## Pending

Five follow-ups, all identified by the chain itself rather than by a person.
Each is its own unit and enters at `writing-plans`:

1. ~~**`pre-edit/02-agent-scope-guard.py` has no caller.**~~ **Closed
   2026-08-16 by narrowing the claim, which was the only honest option** —
   Claude Code spawns subagents itself and runs no hook inside one, so no
   dispatcher in this layer can set `UAIOS_AGENT_NAME`. `workflow.md` now names
   the precondition and says *dormant on this host*;
   `test_agent_standards.py` fails if either stops being true, and also if
   anything starts **setting** the variable — at which point the note is stale
   and the claim can widen again, deliberately.
2. ~~**The ticked-task checkbox is defined four times.**~~ **Closed
   2026-08-20.** All four now share `_hooklib.PROGRESS_TASK_BOX`; `resume`'s
   looser match was not deliberate — tightened to `Task <n>`, which only
   changes behavior for a malformed section, never a well-formed plan.
   `docs/plans/2026-08-20-router-progress-consistency.md` Task 2.
3. ~~**`budget.ELAPSED_CEILING_HOURS = 3.0` is wrong.**~~ **Closed 2026-08-16 by
   dropping the limb, not refitting it.** Re-measured from 147 ledger rows: the
   only unit that ran start to finish (`checklist-completion`) is 19 turns over
   **24.42h**, so the two axes disagreed about one healthy unit and the turn
   axis was right. Wall-clock span measures how long a session stayed open, not
   what the unit cost. Still measured and printed; judged by nothing. The turn
   ceiling stays 30 and was deliberately NOT refit from `security-gate`'s 118 —
   that number is item 11's stale slug, and fitting a ceiling to a measurement
   error bakes the error into the policy.
4. **`ISSUES.md` carries two `0x08` bytes**, in the entry describing `0x08`
   bytes. See `ISSUES.md` 2026-08-11 21:15.

5. ~~**`refs/uaios/green/` has one writer.**~~ **Closed 2026-08-16.**
   `python tools/run_checks.py --tier all --require-test --record-green` is the
   second, refusing before any check runs unless the tier is `all` and unscoped,
   and again unless a test actually ran. Proved on this branch: the state moved
   `BUILD` → `WAITING_DELIVERY`, which the chain had never reached. The
   prediction in the old note was exactly right — the state machine was sound
   and only the plumbing was missing.

Unchanged and still true: branch protection is unavailable on this repo tier
(`403 Upgrade to GitHub Pro`).

**Closed 2026-08-19**: the dead branches were deleted (7 of them — `docs/session-2026-08-09`,
`feat/delivery-check`, `fix/harness-wiring-and-checks-defects`,
`fix/unenforceable-claims`, `merge-framing-into-planning`, `feat/uninstall-verb`,
`fix/delivering-approval-gate`), and `feat/adaptive-workflow` no longer exists
— its plan was absorbed into `feat/security-gate` (PR #12) rather than left
stale.

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
1. ~~Decide whether `feat/checklist-completion` is pushed.~~ **Done 2026-08-19
   — merged as PR #11**, along with PR #12 (`feat/security-gate`); see `LOG.md`.
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

10. ~~**The entry classifier and `workflow.md`'s small-work path disagree,
    and the disagreement favours the less careful route.**~~ **Closed
    2026-08-20, the specific reproduced case.** The classifier's `TOO_SMALL`
    pass now defers to `scope.py`'s own `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS`
    before returning `entry-small`. Traced live during the fix: a fully
    `.claude/...`-qualified path was already caught by an earlier pass; the
    real gap was a bare filename or a non-`.claude` sensitive path
    (`pyproject.toml`, `capability_layer/**`). Widening to the
    `volume`/`spread`/`shared-surface` clauses (which need a real diff, not
    prompt text) is explicitly NOT done — see the plan's Out of Scope.
11. **`resume.py` reported `BUILD` for 57 turns against a stale slug.** It keys
    state to `security-gate` from the branch name; that plan is complete and
    this unit never had one, so there was nothing to advance. Compounds Pending
    5 rather than duplicating it — that one is the green ref never being
    written, this one is the slug pointing at a finished unit. A unit worked
    without a plan is invisible to the chain, which is worth deciding about
    before the small-work path makes plan-less units routine.
12. ~~**A check `timeout` bounds the verdict, not the wall clock.**~~ **Closed
    2026-08-16.** `_projectchecks._run_bounded()` kills the tree the way
    `tools/smoke.py:kill_tree()` already did, and closes the child's stdin.
    Measured both ways: `subprocess.run(timeout=3)` on a 30s command returned
    after **30.1s**; the new path returns in **3.4s** against a 60s command.
    Asserted on elapsed time, since the fix and the bug produce the same verdict
    and the same message.

### Added by the audit unit (2026-08-16)

13. **Objective 2 is the only red, and it is the expensive one.** 17,900 ch
    injected every turn. The one lever is trimming descriptions and the measured
    evidence points the other way — `code-review` scores `trigger_rate 0.0` and
    the docs say the fix for that is a *more* specific description. Needs the
    ~$81 measurement, and its own unit; do not bundle it.
14. ~~**The two routers disagree, reproduced.**~~ **Closed 2026-08-20** —
    same fix as Pending 10 above; both entries describe the same gap found by
    two different sessions. Deterministic routing coverage (33/217, 15%) was
    not re-measured by this fix and may be worth re-checking.
15. **No replacement eval result was written and that is deliberate.**
    `docs/evals/results-2026-08-07.json` is voided in place; the superseding
    numbers live in `ISSUES.md` and `TASK.md` only. Writing them into a results
    file this session did not produce is the same defect with a newer date.
    `python tools/eval_triggers.py` writes a real one, ~$0.45 a query.

### Added by the router-progress-consistency unit (2026-08-20)

16. **`resume.py`'s `BRANCH_PREFIX` only strips one of the five real branch
    prefixes.** `_hooklib.active_plans()` strips `feat/`/`fix/`/`docs/`/
    `chore/`/`refactor/`; `resume.py`'s own `slug_from_branch()` strips only
    `feat/`. Confirmed unrelated to this unit's diff (the function wasn't
    touched), but it meant `resume.py` reported `slug=fix/router-progress-
    consistency` and could not resolve its own active plan all session —
    fed the `chain-continuity` RECON notice for 8+ turns. Full trace in
    `TASK.md`'s Completed entry for this unit.

<!-- session-context:end -->
