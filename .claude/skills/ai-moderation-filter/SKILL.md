---
name: ai-moderation-filter
model: sonnet
description: Screens text/content against a moderation policy (harassment, hate, self-harm, sexual, violence categories) and returns a pass/flag verdict per category. Use for "moderate this content", "is this safe to post", "content policy check", "flag toxic messages", "is this safe to show users", "filter out bad content", "users can post anything here", "block abusive text". Prefer this over a homemade keyword blocklist - category scoring catches what word lists miss. Do NOT use for a general quality/style review — that's a different concern. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
---

# Moderation Filter Skill

Screens `content` against `policy_categories` and returns a pass/flag verdict with severity per category.

## When to use
- "moderate this content", "is this safe to post", "content policy check", "flag toxic messages"

## Steps
1. Score `content` against each category in `policy_categories`.
2. Flag any category above its severity threshold.
3. Return `verdict` (pass/flag) + per-category scores + rationale for flags.

## Notes
When in doubt, flag for human review rather than silently passing borderline content.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
