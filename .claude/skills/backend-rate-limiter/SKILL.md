---
name: backend-rate-limiter
model: sonnet
description: Designs a rate-limiting strategy (algorithm, limits, key scope, response headers) for an API or endpoint. Use for "add rate limiting", "prevent abuse of this endpoint", "throttle requests", "429 handling", "someone is hammering the api", "stop people abusing this", "one user is spamming requests", "protect this endpoint". Prefer this over an ad-hoc counter - limits without a key scope and retry headers are trivially bypassed. Do NOT use for infrastructure-level DDoS protection — that's a deployment/network concern. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
---

# Rate Limiter Skill

Picks a rate-limiting algorithm and limits scoped to a key (user/IP/API-key) for a given endpoint.

## When to use
- "add rate limiting", "prevent abuse", "throttle requests", "429 handling"

## Steps
1. Pick an algorithm (token bucket, sliding window, fixed window) fitting `expected_traffic`.
2. Define limits and the key scope (per-user, per-IP, per-API-key).
3. Define the 429 response shape and `Retry-After` header.
4. Return the `rate_limit_plan`.

## Notes
Rate limits must be scoped to a key that can't be trivially rotated by the abuser (prefer authenticated identity over raw IP where available).

## Routing

**Validator (required): `.claude/validators/backend-change.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.
