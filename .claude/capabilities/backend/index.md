# Backend Capability Package

Purpose: handle backend engineering tasks (APIs, databases, infra-as-code,
observability, performance, debugging).

Keywords: backend, api, database, infra, oauth, observability, server, endpoint, db, sql, migration, auth, login, service, queue, job, cron, slow query, schema, rest, graphql, microservice, rate limit, throttle, 429, background job, async job, cache, caching, invalidate cache, idempotency

Entry point: load this file only when the request matches the `backend`
capability. This file declares available workflows, skills, blueprints and
validators; the runner should then load only the referenced artefacts.

Layout

- `memory/` — capability-local memory snippets

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`backend-`. The copies still under `capabilities/backend/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `backend-oauth`
- `.claude/validators/` — `backend-change`, `backend-oauth`
- `.claude/workflows/` — `backend-oauth`
- `.claude/playbooks/` — `backend-oauth`
- `.claude/templates/` — `backend-api`

Capability Routing

When a backend-related request is detected, load `index.md`, then:

1. If a matching blueprint exists in `.claude/blueprints/` (prefixed `backend-`), prefer it.
2. Else check `.claude/workflows/` (prefixed `backend-`) for a reusable workflow.
3. Else compose from the `backend-` skills in the Skill tool list.

Validators in `.claude/validators/` (prefixed `backend-`) must be run before any side-effects are committed:
`backend-oauth` routes through `.claude/workflows/backend-oauth.md`/`.claude/validators/backend-oauth.md`; every other
backend skill (`backend-rest-api-designer`, `backend-db-migration`, `backend-rate-limiter`,
`backend-background-job`, `backend-caching-strategy`) routes through `.claude/validators/backend-change.md`.

Skills

The 6 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `backend-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `backend-background-job`
- `backend-caching-strategy`
- `backend-db-migration`
- `backend-oauth`
- `backend-rate-limiter`
- `backend-rest-api-designer`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.
