# Coverage Gate Validator — .claude/validators/testing-coverage-gate.md

Purpose: ensure generated tests are deterministic, meaningful, and do not
regress coverage or hide flakiness.

Checks

- New/changed tests pass twice in a row (flakiness check)
- Coverage on touched files does not decrease
- No assertion was weakened or removed to force a pass
- Mutation-testing score (if run) meets the capability's threshold

Failure handling

- Block the test suite from being marked complete; request human review
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "testing-coverage-gate", "capability": "testing"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if a new test blueprint/pattern is promoted.

Usage

Required gate for `unit-test-generator`, `e2e-test-generator`, `mutation-testing`
before the test run is reported as done.
