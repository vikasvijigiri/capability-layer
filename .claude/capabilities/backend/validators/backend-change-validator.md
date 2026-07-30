> **Superseded.** The canonical copy of this file is `.claude/validators/backend-change.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Backend Change Validator — backend/validators/backend-change-validator.md

Purpose: generic gate for backend skills that are not OAuth-specific
(`rest-api-designer`, `db-migration`, `rate-limiter`, `background-job`,
`caching-strategy`) before any side-effect (schema change, deployed config,
infra call) is committed.

Checks

- Migration/config change is reversible or has a documented rollback step
- No secrets or credentials introduced in plain text
- Change matches the frozen API/schema contract for the task
- Tests (unit/integration) pass in sandbox for the affected module

Failure handling

- Block the side-effect and request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "backend-change-validator", "capability": "backend"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the change is captured as a reusable blueprint.

Usage

Required gate for any backend skill without its own dedicated workflow/validator
(everything except `oauth-skill`, which uses `oauth-workflow`/`oauth-validator`).
