---
name: research-citation-scoring
model: opus
description: Scores the credibility and relevance of a source/citation against a claim it's meant to support. Use for "is this a credible source", "score these citations", "does this source actually support the claim", "evidence quality check", "is this a good source", "does this actually back the claim", "can we cite this", "how solid is this evidence". Prefer this over accepting a link at face value - relevance and credibility are different failures. Do NOT use for grammar/style review of the citation text. Gathers evidence only; it does not decide — a decision reached this way still needs recording via `knowledge-manager`.
effort: high
---

# Citation Scoring Skill

Scores whether a source actually supports a claim, and how credible/current the source is.

## When to use
- "is this a credible source", "score these citations", "does this support the claim"

## Steps
1. Check `source` directly supports `claim` (not just topically related).
2. Assess source credibility (peer-reviewed, primary vs. secondary, recency).
3. Return `relevance_score`, `credibility_score`, and a one-line rationale.

## Notes
A topically-related but non-supporting source is a fail, not a partial pass.

## Routing

**Validator (required): `.claude/validators/research-citation-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
