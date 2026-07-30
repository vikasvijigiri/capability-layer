# Testing Capability Package

Purpose: automated test authoring and execution — unit, integration, end-to-end,
mutation, and browser-based tests — plus quality-sweep support before shipping.

Keywords: testing, test, unit test, integration test, e2e, end-to-end, playwright, mutation testing, test coverage, write tests, add tests, run the tests, test this, coverage is thin, browser test, regression suite, pytest, jest, vitest, assertion, fixture, mock, test suite, failing test, coverage

Entry point: load this file for `testing` tasks. It declares skills for
generating and executing deterministic tests, distinct from `debugging`
(diagnosing failures) and `qa-engineer` (the agent that runs this capability).

Layout


Routing

Prefer a blueprint if one exists, else a workflow, else compose from the `testing-` skills in the Skill tool list.
Treat production code as read-only — a failing test is never fixed by
weakening the assertion. Always run `.claude/validators/testing-coverage-gate.md` before reporting done.

Skills

The 3 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `testing-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `testing-e2e-test-generator`
- `testing-mutation-testing`
- `testing-unit-test-generator`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`testing-`. The copies still under `capabilities/testing/` are superseded and
must not be linked to.

- `.claude/validators/` — `testing-coverage-gate`
