# 04 — Skill System

## Purpose
Skills are versioned, domain-specific capabilities (code + prompts + tests)
exposed to the Planner and router.

## Skill Model
- Interface: inputs, outputs, preconditions, side-effects.
- Versions: semantic versioning with metrics.
- Metrics: success rate, latency, token usage.

## Lifecycle
1. Implement
2. Test (unit + integration)
3. Register with router
4. Monitor and iterate

## Examples
- `deploy:fastapi-on-ecs`
- `db:postgres-deadlock-diagnose`

See [16-Domain Skill Packs](16-domain-skill-packs.md).