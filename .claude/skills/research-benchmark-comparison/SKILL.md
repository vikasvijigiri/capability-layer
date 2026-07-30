---
name: research-benchmark-comparison
model: opus
description: Runs or aggregates quantitative benchmarks across candidate solutions and reports statistically sound comparisons. Use for "benchmark these", "which is faster/cheaper", "performance comparison", "benchmark this against alternatives", "which one is faster", "which is cheaper", "measure them against each other", "is it actually better". Prefer this over quoting vendor claims - a measured comparison is the only one that survives a follow-up question. Do NOT use for a qualitative/feature comparison with no numeric measurement — that's competitive-analysis. Gathers evidence only; it does not decide — a decision reached this way still needs recording via `knowledge-manager`.
---

# Benchmark Comparison Skill

Runs `benchmark_scenario` against each candidate and reports results with variance, not just a single point estimate.

## When to use
- "benchmark these", "which is faster/cheaper", "performance comparison"

## Steps
1. Run `benchmark_scenario` against each entry in `candidates`, multiple iterations.
2. Report mean, variance, and outliers per candidate.
3. Return `benchmark_report` with the methodology stated explicitly.

## Notes
A single run is an anecdote, not a benchmark — always run enough iterations to report variance.

## Routing

**Validator (required): `.claude/validators/research-citation-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
