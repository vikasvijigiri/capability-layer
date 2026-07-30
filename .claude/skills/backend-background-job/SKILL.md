---
name: backend-background-job
model: sonnet
description: Designs a background/async job (queue choice, retry policy, idempotency key, dead-letter handling) for long-running or deferred work. Use for "run this in the background", "add a queue", "async job", "retry on failure", "cron job design", "this takes too long in the request", "do it after responding", "send the email without blocking", "process this later". Prefer this over a fire-and-forget thread - retries, idempotency and dead-lettering are what make deferred work safe. Do NOT use for synchronous request/response work with no deferred execution need. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
---

# Background Job Skill

Designs a queued/async job with a retry policy, idempotency key, and dead-letter path.

## When to use
- "run this in the background", "add a queue", "async job", "cron job design"

## Steps
1. Choose a queue/scheduling mechanism fitting `expected_volume`.
2. Define an idempotency key so retries can't double-process.
3. Define retry policy (backoff, max attempts) and dead-letter handling.
4. Return the `job_design`.

## Notes
Every job must be safely retryable — no job design without an idempotency key is complete.

## Routing

**Validator (required): `.claude/validators/backend-change.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.
