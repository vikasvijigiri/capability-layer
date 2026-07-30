---
name: ai-text-classification
model: sonnet
description: Classifies text into a fixed label set (intent, sentiment, category, priority) with confidence scores. Use for "classify this", "what category is this", "sentiment of this text", "intent detection", "tag this ticket/email", "sort these automatically", "tag incoming tickets", "work out what this is about", "route these to the right team". Prefer this over hand-written if/else rules once the label set is fixed. Do NOT use for open-ended extraction with no fixed label set — that's a different task. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
---

# Text Classification Skill

Assigns one (or more) labels from a fixed `label_set` to input text, with a confidence score per label.

## When to use
- "classify this", "what category/intent/sentiment is this", "tag this ticket"

## Steps
1. Confirm `label_set` is fixed and mutually exclusive (or explicitly multi-label).
2. Score `text` against each label.
3. Return top label(s) + confidence + a one-line rationale.

## Notes
Never invent a label outside `label_set` — if nothing fits, return `unclassified` rather than guessing.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
