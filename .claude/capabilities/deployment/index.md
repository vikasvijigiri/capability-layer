# Deployment Capability Package

Purpose: deployments, infrastructure-as-code, release orchestration, and
cloud cost control.

Keywords: deployment, infra, ci, cd, canary, provisioning, deploy, host, publish, ship it, put online, release, rollout, pipeline, github actions, docker, live url, secrets, env vars, api keys, health check, readiness probe, liveness probe

Entry point: load this file for `deployment` tasks. It enumerates workflows,
skills, and validators for safe deployment.

Layout

- `mcp/` — mappings to CI/CD and cloud MCPs

Routing

Prefer blueprints, then workflows, then skills. Always run validators and
smoke tests before promoting to production.

Skills

The 5 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `deployment-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `deployment-canary-promotion`
- `deployment-health-check-endpoint`
- `deployment-infra-provision`
- `deployment-rollback`
- `deployment-secrets-provisioning`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`deployment-`. The copies still under `capabilities/deployment/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `deployment-canary`
- `.claude/validators/` — `deployment-smoke-test`
- `.claude/workflows/` — `deployment-pipeline`
