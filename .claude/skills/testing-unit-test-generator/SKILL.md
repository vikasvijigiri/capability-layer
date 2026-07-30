---
name: testing-unit-test-generator
model: haiku
description: Generates deterministic unit tests (happy path, edge cases, error cases) for a given function/module. Use for "write unit tests", "add tests for this function", "test coverage is thin", "cover the edge cases", "this function has no tests", "make sure this keeps working". Prefer this over testing only the happy path - error and boundary cases are where regressions land. Do NOT use for browser/UI-level tests — that's e2e-test-generator. Generates tests only; to run a suite, own coverage end-to-end or sweep for stale tests, use the `qa-engineer` agent.
---

# Unit Test Generator Skill

Generates deterministic unit tests covering happy path, boundary, and error cases for `target_module`, avoiding duplication of `existing_tests`.

## When to use
- "write unit tests", "add tests for this function", "cover the edge cases"

## Steps
1. Read `target_module` and enumerate its public behavior and edge cases.
2. Check `existing_tests` to avoid duplicate coverage.
3. Generate tests with clear arrange/act/assert structure and no shared mutable state.
4. Run the new suite and report pass/fail.

## Notes
Never weaken an assertion to make a test pass — a red test reveals a real bug or a wrong test, never a reason to loosen it.

## Routing

**Validator (required): `.claude/validators/testing-coverage-gate.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
