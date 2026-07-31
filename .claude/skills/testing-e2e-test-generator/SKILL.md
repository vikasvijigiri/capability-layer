---
name: testing-e2e-test-generator
model: haiku
description: Generates browser-driven end-to-end tests (Playwright-style) covering critical user flows. Use for "add e2e tests", "browser test this flow", "playwright test", "test the whole signup flow", "test the whole flow", "make sure signup still works", "test it like a user would", "check the happy path end to end". Prefer this over manual click-through - a flow nobody re-tests is a flow that silently breaks. Do NOT use for isolated function-level logic — that's unit-test-generator. Generates tests only; to run a suite, own coverage end-to-end or sweep for stale tests, use the `qa-engineer` agent.
effort: low
---

# E2E Test Generator Skill

Generates browser-driven tests for `user_flow` against `app_url_or_build`, using stable selectors and explicit waits.

## When to use
- "add e2e tests", "browser test this flow", "playwright test"

## Steps
1. Break `user_flow` into discrete steps (navigate, act, assert).
2. Use stable selectors (roles/test-ids), never brittle CSS/XPath position-based ones.
3. Add explicit waits for async state instead of fixed sleeps.
4. Run the suite headless and report pass/fail with screenshots on failure.

## Notes
A flaky e2e test is a bug in the test, not an excuse to add a longer sleep — route persistent flakiness to `flaky-test-diagnoser`.

## Routing

**Validator (required): `.claude/validators/testing-coverage-gate.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
