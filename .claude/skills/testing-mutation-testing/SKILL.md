---
name: testing-mutation-testing
model: haiku
description: Injects small code mutations and checks whether the existing test suite catches them, to measure real test effectiveness beyond line coverage. Use for "mutation testing", "are these tests actually good", "test effectiveness", "coverage looks high but is it meaningful", "are these tests any good", "coverage is high but I don't trust it", "do the tests actually catch bugs", "is the suite worth anything". Prefer this over reading a coverage percentage - executed lines and asserted behaviour are different things. Do NOT use as a substitute for writing tests in the first place — it only measures suites that already exist. Generates tests only; to run a suite, own coverage end-to-end or sweep for stale tests, use the `qa-engineer` agent.
---

# Mutation Testing Skill

Injects small mutations (flipped conditionals, off-by-one, swapped operators) into `target_module` and checks whether `test_suite` catches each one.

## When to use
- "mutation testing", "are these tests actually good", "coverage looks high but is it meaningful"

## Steps
1. Generate a set of small semantic mutations in `target_module`.
2. Run `test_suite` against each mutant.
3. Report the mutation score (mutants killed / total) and list surviving mutants with their location.

## Notes
A surviving mutant means a real gap in the assertions, not just missing line coverage — prioritize fixing those over adding more tests elsewhere.

## Routing

**Validator (required): `.claude/validators/testing-coverage-gate.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
