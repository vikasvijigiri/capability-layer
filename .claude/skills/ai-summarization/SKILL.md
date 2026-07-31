---
name: ai-summarization
model: sonnet
description: Produces a length- and style-controlled summary of long text (extractive or abstractive) while preserving key facts and figures. Use for "summarize this", "give me the TL;DR", "condense this document", "executive summary of this", "too long to read", "shorten this", "give me the gist", "what does this say in short". Prefer this over truncating text - length control that preserves the key facts is the whole point. Do NOT use when the ask is really "extract structured fields" — that's api-extractor/text-classification territory. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
effort: medium
---

# Summarization Skill

Condenses `source_text` to `target_length` in the requested `style` (bullet, executive, one-liner) without dropping key facts/figures.

## When to use
- "summarize this", "TL;DR", "condense this doc", "executive summary"

## Steps
1. Identify key facts, figures, and conclusions that must survive compression.
2. Draft the summary at `target_length` in `style`.
3. Verify every retained claim traces back to `source_text` (no added claims).

## Notes
Never introduce a fact/number not present in `source_text` — summarizing is compression, not synthesis.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
