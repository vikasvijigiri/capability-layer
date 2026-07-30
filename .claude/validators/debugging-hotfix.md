# Hotfix Validator — .claude/validators/debugging-hotfix.md

Purpose: validate that a proposed hotfix is safe to apply.

Checks

- Unit and integration tests pass in sandbox
- No security-sensitive code paths modified without review
- Rollback plan exists

Failure handling

- Block hotfix and request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "debugging-hotfix", "capability": "debugging"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the fix is captured as a reusable blueprint.

Usage

Gate for `.claude/workflows/debugging-repro.md` and for any fix produced by `log-parser`, `profiler-orchestrator`, `memory-leak-detector`, `flaky-test-diagnoser` before it is applied.
