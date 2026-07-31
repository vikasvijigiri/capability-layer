---
name: ai-model-router
model: opus
description: Picks the cheapest/most-capable model for a task from a declared candidate list based on task complexity, latency and cost constraints. Use for "which model should handle this", "route this to a cheaper model", "model selection", "cost vs quality tradeoff for LLM calls", "this is costing too much", "can we use a cheaper model", "which model should we use here", "the bill is going up". Prefer this over hardcoding one model everywhere - an unexamined model choice becomes a fixed cost. Do NOT use for a single fixed-model project with no routing decision. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
effort: high
---

# Model Router Skill

Chooses which model/tier should handle a request given complexity, cost ceiling, and latency budget.

## When to use
- "which model for this", "route to cheaper/faster model", "model tiering", "cost cap on LLM calls"

## Steps
1. Classify task complexity (simple/medium/complex).
2. Filter `candidate_models` by `constraints` (cost ceiling, latency, context length).
3. Pick the cheapest model meeting the complexity bar.
4. Return `model`, `rationale`, `estimated_cost`.

## Notes
Prefer the smallest model that clears the complexity bar — never the largest by default.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
