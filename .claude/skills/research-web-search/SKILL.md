---
name: research-web-search
model: opus
description: Runs a scoped web search and returns ranked, deduplicated results with source metadata. Use for "look this up", "search the web for", "find sources on", "what's out there about X", "find out about this", "what's out there on this", "is there anything written about this". Prefer this over answering from memory when the answer may have changed recently. Do NOT use for an already-open, well-defined internal codebase question — use Explore instead. Gathers evidence only; it does not decide — a decision reached this way still needs recording via `knowledge-manager`.
---

# Web Search Skill

Runs a scoped search for a query and returns ranked, deduplicated, sourced results.

## When to use
- "look this up", "search for", "find sources on", "what's out there about X"

## Steps
1. Run the search for `query`.
2. Deduplicate and rank by relevance/recency.
3. Return `results[]` with title, url, snippet.

## Notes
Never fabricate a URL or citation — every result must come from an actual search hit.

## Routing

**Validator (required): `.claude/validators/research-citation-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
