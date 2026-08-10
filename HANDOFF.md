# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

The chain has run end to end more than once, and on 2026-08-10 it ran **on the
layer itself**: spec → plan → Gate 1 → execute → verify → sweep → review →
record, with three recovery loops back into repair. See `LOG.md` 2026-08-10 18:40.

**Parallel subagent dispatch works.** This file previously said *"No subagent has
ever completed a task."* That is no longer true — two agents, one message,
disjoint files, proved by reading their worktrees.

<!-- session-context:start -->

## Current Work

Branch `feat/target-workflow`, 9 commits ahead of `main` (`c21763b..1a1abc0`),
`37 files changed, 4065 insertions(+)`. **Nothing is pushed and no PR is open.**

The target-workflow plan is complete: 9/9 tasks ticked, each with a quoted
verification, `code-review` returned `passed: true` after four findings were
repaired, and the full tier closes at `PASS: 42 check(s) green (audit, build,
lint, smoke, test, typecheck)`.

Three further units landed on the same branch and are also reviewed: chain
continuity, risk tiering, and the memory read side.

## Pending

- **`GOAL_CHECKLIST.md` is untracked at the repo root** — 148 lines, a 15-stage
  production-grade checklist supplied by the user. It is the input document for
  the next unit and is deliberately not committed yet; the minimal-diff gate
  refuses it because no plan declares it. Declare it or commit it as part of that
  unit's plan.
- **The remaining checklist scope is not planned yet.** An audit of the layer
  against all 77 of its lines is at
  `https://claude.ai/code/artifact/681a1cb1-6c26-4474-9c6f-82a9e039d3ec`:
  21 mechanism, 23 partial, 4 prose-only, 29 absent. This is the next unit and it
  enters at `writing-plans`, not by continuing to build on the finished plan.
- **Branch protection is still unavailable, not merely unset.** `403 Upgrade to
  GitHub Pro or make this repository public`. Unchanged, and not actionable.
- **Seven branches are fully merged into `main`** and are dead weight:
  `docs/session-2026-08-09`, `feat/delivery-check`, `feat/uninstall-verb`,
  `fix/delivering-approval-gate`, `fix/unenforceable-claims`,
  `merge-framing-into-planning`, `reconcile/stranded-units`.
- **`feat/adaptive-workflow` @ `076914e` carries a superseded plan** whose unique
  content was folded into the target-workflow plan. Nothing marks it superseded
  and it is invisible from `main`; if that branch merges, an unapproved plan
  lands.

## Next Steps

1. Decide what to do with `GOAL_CHECKLIST.md` — track it, or declare it in the
   next plan.
2. Take the remaining checklist scope through `writing-plans`. It will now tier
   itself (`scope.py --plan`) and query `tools/memory.py` for the paths it
   touches. Gate 1 is `ExitPlanMode`.
3. Push and open a PR for `feat/target-workflow` when you want it landed — that
   needs an explicit yes, and `tools/delivery_check.py` should be quoted first.

## Open Questions

- **What is honestly buildable of §12–§14?** Staging rehearsal, release, rollback
  and post-release smoke all have real implementations here if the deployable
  artefact is taken to be *the wheel installed into a target repository* —
  `test_package.py` already does the rehearsal and `install.py uninstall` is a
  genuine rollback. **Canary rollout, production metrics and automatic rollback
  on error rate have no honest implementation**: there is no running service.
  Writing skills that describe them would reproduce the exact defect the audit
  measured.
- **Nothing forces a chain handoff, and nothing can.** A hook may not invoke a
  skill (`decisions/2026-08-04-hooks-never-name-a-skill.md`).
  `post-run/08-chain-continuity.py` makes a missed handoff loud instead of
  silent, which is the ceiling. Whether an external driver (`tools/drive.py`) is
  worth building should be decided from the ledger it now writes, not from
  argument.

<!-- session-context:end -->
