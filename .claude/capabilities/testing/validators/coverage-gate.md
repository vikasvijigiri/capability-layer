> **Superseded.** The canonical copy of this file is `.claude/validators/testing-coverage-gate.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Coverage Gate Validator — testing/validators/coverage-gate.md

Purpose: ensure generated tests are deterministic, meaningful, and do not
regress coverage or hide flakiness.

Checks

- New/changed tests pass twice in a row (flakiness check)
- Coverage on touched files does not decrease
- No assertion was weakened or removed to force a pass
- Mutation-testing score (if run) meets the capability's threshold

Failure handling

- Block the test suite from being marked complete; request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "coverage-gate", "capability": "testing"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if a new test blueprint/pattern is promoted.

Usage

Required gate for `unit-test-generator`, `e2e-test-generator`, `mutation-testing`
before the test run is reported as done.
