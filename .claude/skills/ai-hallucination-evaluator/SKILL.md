---
name: ai-hallucination-evaluator
model: sonnet
description: Scores a generated answer against its cited source evidence for factual grounding. Use for "is this answer hallucinating", "check this response against sources", "evaluate LLM output for accuracy", "fact-check this generation", "is this made up", "can I trust this output", "it sounds confident but wrong", "check it against the source". Prefer this over eyeballing a generated answer - confident wrong output reads exactly like correct output. Do NOT use for subjective quality/style review — that's a different concern. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
effort: medium
---

# Hallucination Evaluator Skill

Checks whether every claim in an answer is traceable to the supplied evidence.

## When to use
- "check for hallucination", "fact-check this answer", "does this response match the sources"

## Steps
1. Split `answer` into atomic claims.
2. Match each claim against `evidence_snippets`.
3. Flag unsupported or contradicted claims.
4. Return `score` (0-100%) + `unsupported_claims[]`.

## Notes
A claim with no matching evidence is unsupported, not "probably fine" — flag it.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
