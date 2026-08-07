# Handoff

<!-- Current-state snapshot. Rewrite this file at each meaningful handoff;
history belongs in LOG.md and TASK.md's Completed section. -->

## Completed

- Replaced `skill-authoring` with `capability-layer-maintenance`.
- Made `.claude/` the canonical capability layer and moved the harness manifest
  to root `harnesses.json`.
- Added read-only capability drift detection and hook-policy validation.
- Changed SessionStart documentation bootstrap from authoring to detection.
- Verified the complete repository suite: 22 checks green.
- Cleared a 130-file uncommitted backlog into five reviewed commits.
- Added derived-state resume (`tools/resume.py`), failure classification
  (`_hooklib.FAILURE_CLASSES`) and the bounded escalation ladder with a
  verified-green restore point (`tools/loop.py`). 25 checks green, both tiers.
- Removed CLAUDE.md's enforced 320-line ceiling; the check is now opt-in.

## Current Work

Branch `rebuild-capability-layer`, not pushed. The canonical layer is `.claude/`;
`AGENTS.md` and `harnesses.json` define the harness-neutral contract. Workflow
state is no longer described in prose — `tools/resume.py` derives it from git,
and `decisions/2026-08-07-derived-state-over-stored-state.md` says why.

## Pending

- **Nothing has ever been pushed.** No remote exists, so the `merge_group`
  trigger, the `conclusion` required check and `CODEOWNERS` are correct as files
  and unproven against GitHub. `/publish` when you want that closed;
  `[state:no-remote]` says so at session start.
- Canary release (`release.yaml` thresholds, auto-rollback) is unbuilt on
  purpose — there is no deploy target, so every assertion would test a mock.
  It belongs in a repo that deploys something.
- Skills went 22 → 13 by folding techniques into the stage that uses them.
  `task-brief`+`brainstormer` and `verifying-work`+`systematic-debugging` were
  deliberately left apart: their triggers are genuinely different and merging
  them trades routing precision for ~200 tokens.
- Populate and maintain `README.md` as stable project documentation.
- Refresh stale historical entries only when they are no longer useful as
  history; do not rewrite `LOG.md` merely to remove old names.
- Perform a real IDE-hosted product-task pilot to prove live workflow behavior.
- Confirm the first real SessionStart state-report run in a fresh session.

## Next Steps

1. Use `capability-layer-maintenance` for capability-layer contract changes.
2. Use `knowledge-manager` for README, TASK, HANDOFF, MEMORY, LOG, ISSUES, and
   decision updates.
3. Run `python tools/run_checks.py --tier all --require-test` before completion
   claims.

## Open Questions

- Which product repository will provide the first real host-managed workflow
  pilot?
- Which deploy target, if any, should be used for release verification?
