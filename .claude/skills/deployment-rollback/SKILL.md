---
name: deployment-rollback
model: haiku
description: Generates a safe rollback plan and executes it to restore the last known-good deployed version. Use for "roll this back", "revert the deploy", "undo the release", "the new version is broken, go back", "put the old version back", "the new version is broken", "revert what we just shipped". Prefer this over debugging live - restoring known-good first buys time to diagnose properly. Do NOT use for a code-level git revert with no live deployment involved. One step of a release; for an end-to-end deploy with secrets, health checks and live-URL verification, use `deployment-pilot`.
---

# Rollback Skill

Restores the last known-good deployed version and verifies health after rollback.

## When to use
- "roll back the deploy", "revert the release", "undo this deployment", "prod is broken, go back"

## Steps
1. Confirm `last_known_good_version` and its health status.
2. Execute the rollback (redeploy previous artifact/tag).
3. Run smoke tests / health check against the rolled-back version.
4. Report `status` + `health_check_result`.

## Notes
Requires human approval before executing in a shared/production environment.

## Routing

**Validator (required): `.claude/validators/deployment-smoke-test.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/deployment-canary.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/deployment-pipeline.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
