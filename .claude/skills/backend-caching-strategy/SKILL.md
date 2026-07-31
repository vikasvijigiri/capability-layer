---
name: backend-caching-strategy
model: sonnet
description: Picks a caching layer, key scheme, TTL and invalidation strategy for a slow or expensive read path. Use for "cache this", "this query is slow", "add a cache layer", "cache invalidation strategy", "the same query runs constantly", "this page takes ages to load", "we hit the database too much", "make it faster without changing the logic". Prefer this over adding an index and hoping - key scheme and invalidation are where caching actually goes wrong. Do NOT use for a genuinely fast read path with no measured latency problem. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
effort: medium
---

# Caching Strategy Skill

Designs a cache layer (key scheme, TTL, invalidation trigger) for a specific slow read path.

## When to use
- "cache this", "slow query", "add a cache layer", "cache invalidation"

## Steps
1. Confirm the read path is actually slow/expensive, not just perceived so.
2. Define key scheme and TTL fitting `staleness_tolerance`.
3. Define the invalidation trigger (write-through, event-based, TTL-only).
4. Return the `caching_plan`.

## Notes
Never cache without an explicit invalidation trigger — a TTL-only cache on frequently-changing data is a correctness bug waiting to happen.

## Routing

**Validator (required): `.claude/validators/backend-change.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.
