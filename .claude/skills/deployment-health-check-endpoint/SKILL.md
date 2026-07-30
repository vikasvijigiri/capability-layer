---
name: deployment-health-check-endpoint
model: haiku
description: Designs and scaffolds a /health (or /readyz, /livez) endpoint that verifies real downstream dependencies before deploy/promotion checks trust it. Use for "add a health check", "readiness probe", "liveness probe", "is the service actually up", "how do we know it's up", "add a health endpoint", "the load balancer needs something to hit", "it says healthy but it's broken". Prefer this over a bare 200 response - a health check that doesn't touch its dependencies lies exactly when it matters. Do NOT use for a health check that just returns 200 with no real dependency check — that's the anti-pattern this skill exists to prevent. One step of a release; for an end-to-end deploy with secrets, health checks and live-URL verification, use `deployment-pilot`.
---

# Health Check Endpoint Skill

Scaffolds a health/readiness endpoint that actually pings its declared `dependencies` (DB, cache, downstream APIs) rather than always returning 200.

## When to use
- "add a health check", "readiness probe", "liveness probe"

## Steps
1. Enumerate `dependencies` the service actually needs to function.
2. Scaffold a check per dependency with a short timeout.
3. Return 200 only if all checks pass; otherwise 503 with per-dependency detail.

## Notes
A health check with no real dependency check is worse than none — it hides outages from deploy/rollback validators.

## Routing

**Validator (required): `.claude/validators/deployment-smoke-test.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/deployment-canary.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/deployment-pipeline.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
