---
name: debugging-log-parser
model: sonnet
description: Parses log files and correlates error traces by request id to surface suspected root causes. Use for "parse these logs", "correlate errors across services", "find the root cause in logs", "why is this failing in prod", "stack trace analysis", "something is wrong in production", "dig through the logs", "what happened at 3am", "users are seeing errors". Prefer this over scrolling logs by hand - correlating by request id is what turns noise into a cause. Do NOT use to apply a fix — this skill only analyzes. Scoped to a single diagnostic technique; for the overall bounded diagnose-fix-reverify loop on a repeatedly failing check, use `error-recovery`.
---

# Log Parser Skill

Parses logs and extracts correlated error traces across a request lifecycle.

## When to use
- "parse logs", "correlate errors", "root cause in logs", "stack trace analysis"

## Steps
1. Ingest logs, index by request id.
2. Correlate spans and errors across services.
3. Produce suspected root causes + stack trace summaries.

## Notes
Read-only — never modifies production systems. Hand findings to `error-recovery` for the fix loop.

## Routing

**Validator (required): `.claude/validators/debugging-hotfix.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/debugging-rca.md` - a matching blueprint takes precedence over a hand-built solution.
