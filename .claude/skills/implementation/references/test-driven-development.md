---
name: test-driven-development
description: Drive implementation from executable tests - define behaviour, write a failing test, make the smallest change, refactor, prove regression coverage. For new behaviour, bug fixes, risky refactors, APIs, boundary conditions. Do NOT use as a substitute for system-level verification or exploratory testing.
when_to_use: when new or changed behavior needs executable proof
effort: high
model: sonnet
disable-model-invocation: false
---

# Test-Driven Development

Use the smallest test that makes the requested behavior undeniable. Keep the
test and production change in the same bounded task.

## Cycle

1. Translate the brief into observable behavior and identify the boundary,
   failure mode, and acceptance evidence.
2. Locate the nearest existing test style and write one focused failing test.
   Run it and record the failure; a test that never failed is not proof that it
   exercises the new behavior.
3. Implement the smallest production change that makes the test pass. Do not
   broaden the change to clean unrelated code.
4. Run the focused test, then the nearest regression suite.
5. Refactor only after green: remove duplication, clarify names, and preserve
   the behavior with the tests still green.
6. Add edge tests for empty/null input, invalid input, dependency failure,
   concurrency, limits, retries, and authorization when applicable.

## Quality rules

- Test behavior at the public boundary; avoid tests coupled to private layout.
- Prefer deterministic fixtures and controlled clocks/randomness.
- Assert useful failure messages and state transitions, not only status codes.
- Keep integration and end-to-end tests for contract boundaries; do not replace
  all unit tests with slow system tests.
- Never hide a failing test, weaken an assertion, or mark a test skipped without
  a named reason and follow-up.

## Evidence

Report the red test, green test, regression command, and any untested boundary.
Hand the result to `testing`; use `debugging` when the test
fails for an unexplained reason.

## Next step

Return the tested change and evidence to `implementation`, then `testing`.

## Routing

- Enter for new behavior, bug fixes, risky refactors, or acceptance criteria
  that need executable proof.
- Pair with `architecture` for UI behavior and `code-review` (accessibility lens) for interface
  semantics.
- Do not use for a documentation-only change unless the documentation is an
  executable contract.

## Success

The behavior has a focused test that was observed failing, the smallest change
makes it pass, regression tests remain green, and the remaining evidence gaps
are explicit.
