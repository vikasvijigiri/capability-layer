---
name: debugging-flaky-test-diagnoser
model: sonnet
description: Identifies why a test fails intermittently (timing, shared state, ordering, external dependency) by running it repeatedly under varied conditions. Use for "this test is flaky", "fails intermittently", "passes locally, fails in CI", "test ordering issue", "sometimes it passes sometimes it doesn't", "it's flaky", "green locally red in CI", "just re-run it and it works". Prefer this over retrying the job - a re-run that passes hides the shared state or ordering bug that caused it. Do NOT use for a test that fails deterministically — that's a real bug, not flakiness. Scoped to a single diagnostic technique; for the overall bounded diagnose-fix-reverify loop on a repeatedly failing check, use `error-recovery`.
---

# Flaky Test Diagnoser Skill

Runs a suspected-flaky test repeatedly under varied conditions (order, parallelism, timing) to isolate the cause.

## When to use
- "this test is flaky", "fails intermittently", "passes locally fails in CI"

## Steps
1. Re-run `test_id` N times in isolation, then N times alongside its usual suite.
2. Vary execution order and parallelism between runs.
3. Correlate failures with shared state, timing assumptions, or external dependencies.
4. Return `flakiness_report` with the isolated root cause.

## Notes
"Just re-run it" is not a diagnosis — this skill exists specifically to avoid that non-answer.

## Routing

**Validator (required): `.claude/validators/debugging-hotfix.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/debugging-rca.md` - a matching blueprint takes precedence over a hand-built solution.
