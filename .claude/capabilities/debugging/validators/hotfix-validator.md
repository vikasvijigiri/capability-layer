> **Superseded.** The canonical copy of this file is `.claude/validators/debugging-hotfix.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Hotfix Validator — debugging/validators/hotfix-validator.md

Purpose: validate that a proposed hotfix is safe to apply.

Checks

- Unit and integration tests pass in sandbox
- No security-sensitive code paths modified without review
- Rollback plan exists

Failure handling

- Block hotfix and request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "hotfix-validator", "capability": "debugging"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the fix is captured as a reusable blueprint.

Usage

Gate for `repro-workflow` and for any fix produced by `log-parser`, `profiler-orchestrator`, `memory-leak-detector`, `flaky-test-diagnoser` before it is applied.
