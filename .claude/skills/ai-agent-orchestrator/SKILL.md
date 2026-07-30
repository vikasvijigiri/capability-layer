---
name: ai-agent-orchestrator
model: sonnet
description: Plans and coordinates multiple sub-agents (e.g. small models for cheap subtasks, a larger model for synthesis) against a shared task, merging their outputs. Use for "coordinate multiple agents", "use sub-agents for this", "split this across agents", "big model plans, small models execute", "too big for one pass", "run these in parallel", "one plans, the others execute", "have one plan and others do the work". Prefer this over one long single-model pass when subtasks are genuinely independent. Do NOT use for a single-model, single-step task - that's overkill. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
---

# Agent Orchestrator Skill

Splits a task across `available_agents`, assigning cheaper models to bounded subtasks and reserving synthesis for the strongest model.

## When to use
- "coordinate multiple agents", "use sub-agents", "split this across agents"

## Steps
1. Decompose `task` into independent subtasks.
2. Assign each subtask to the cheapest capable agent in `available_agents`.
3. Collect subtask outputs and merge/synthesize with the strongest agent.
4. Return the merged result + per-subtask attribution.

## Notes
Subtasks must be genuinely independent (disjoint inputs/outputs) — don't split work with shared mutable state across agents.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
