---
name: deployment-canary-promotion
model: haiku
description: Gradually shifts traffic from a canary to full production based on live health metrics, with automatic halt on regression. Use for "promote the canary", "gradual rollout", "shift traffic to the new version", "blue-green promotion", "roll it out slowly", "send a bit of traffic to the new one first", "don't switch everyone at once", "ramp it up". Prefer this over an all-at-once switch - halting on a metric regression is the point. Do NOT use for an all-at-once deploy with no staged traffic shift. One step of a release; for an end-to-end deploy with secrets, health checks and live-URL verification, use `deployment-pilot`.
---

# Canary Promotion Skill

Steps traffic from canary to full production, halting automatically if health thresholds are breached.

## When to use
- "promote the canary", "gradual rollout", "shift traffic", "blue-green promotion"

## Steps
1. Shift traffic to the first step in `traffic_steps`.
2. Check metrics against `health_thresholds`; halt and roll back on breach.
3. Repeat until 100% traffic or a halt condition triggers.
4. Report final `traffic_percentage` + `status`.

## Notes
Any threshold breach halts promotion and triggers `rollback` — never proceeds past a failed check.

## Routing

**Validator (required): `.claude/validators/deployment-smoke-test.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/deployment-canary.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/deployment-pipeline.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
