---
name: debugging-repro-script
model: sonnet
description: Builds a minimal, deterministic reproduction script/test for a reported bug before any fix is attempted. Use for "reproduce this bug", "I can't reproduce it", "write a failing test for this issue", "minimal repro case", "works on my machine", "it only happens for some users", "it only happens sometimes", "need a failing test first". Prefer this over fixing from the description alone - a fix with no repro cannot be shown to have worked. Do NOT use once a reliable repro already exists. Scoped to a single diagnostic technique; for the overall bounded diagnose-fix-reverify loop on a repeatedly failing check, use `error-recovery`.
---

# Repro Script Skill

Turns a bug report into the smallest deterministic script/test that reliably reproduces the failure.

## When to use
- "reproduce this bug", "can't repro", "write a failing test for this", "minimal repro"

## Steps
1. Extract preconditions and trigger steps from `bug_report`.
2. Strip everything not required to trigger the failure.
3. Encode as a runnable script/test that fails deterministically.
4. Confirm it fails before handing off to a fix.

## Notes
A repro that doesn't reliably fail is not done — iterate until it's deterministic.

## Routing

**Validator (required): `.claude/validators/debugging-hotfix.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/debugging-rca.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/debugging-repro.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
