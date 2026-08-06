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

## Current Work

Branch `rebuild-capability-layer`, 73 commits, not pushed. The repository has
22 skills, 10 agents, 11 registered hooks, 11 commands, and one dynamic
workflow. The canonical layer is `.claude/`; `AGENTS.md` and `harnesses.json`
define the harness-neutral contract.

## Pending

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
