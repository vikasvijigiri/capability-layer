---
name: research-competitive-analysis
model: opus
description: Compares a set of competing products/approaches against defined criteria and produces a scored comparison matrix. Use for "compare these options", "competitive analysis", "how do we stack up against X", "which alternative is best for our case", "how do we compare to them", "what else is out there", "what are the alternatives". Prefer this over an impression - a scored matrix makes the criteria visible and arguable. Do NOT use for a single-option feasibility check — that's just research, not comparison. Gathers evidence only; it does not decide — a decision reached this way still needs recording via `knowledge-manager`.
---

# Competitive Analysis Skill

Scores each entry in `candidates` against `criteria` and produces a comparison matrix with a recommendation.

## When to use
- "compare these options", "competitive analysis", "which alternative is best for us"

## Steps
1. Confirm `criteria` are weighted and mutually understood.
2. Score each candidate against each criterion with evidence.
3. Produce the `comparison_matrix` + a recommendation with rationale.

## Notes
Every score must cite evidence (docs, benchmarks, pricing pages) — no score without a traceable source.

## Routing

**Validator (required): `.claude/validators/research-citation-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
