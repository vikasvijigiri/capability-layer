# Backend Change Validator — .claude/validators/backend-change.md

Purpose: generic gate for backend skills that are not OAuth-specific
(`backend-rest-api-designer`, `backend-db-migration`, `backend-rate-limiter`, `backend-background-job`,
`backend-caching-strategy`) before any side-effect (schema change, deployed config,
infra call) is committed.

Checks

- Migration/config change is reversible or has a documented rollback step
- No secrets or credentials introduced in plain text
- Change matches the frozen API/schema contract for the task
- Tests (unit/integration) pass in sandbox for the affected module

Failure handling

- Block the side-effect and request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "backend-change", "capability": "backend"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the change is captured as a reusable blueprint.

Usage

Required gate for any backend skill without its own dedicated workflow/validator
(everything except `backend-oauth`, which uses `.claude/workflows/backend-oauth.md`/`.claude/validators/backend-oauth.md`).
