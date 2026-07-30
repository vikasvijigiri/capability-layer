# AI Capability Package

Purpose: provide AI-specific skills (prompt engineering, RAG, embeddings,
model routing, evaluation, hallucination checks).

Keywords: ai, rag, embeddings, hallucination, evaluation, model-routing, llm, prompt, chatbot, genai, vector search, semantic search, retrieval, fine-tune, agent, gpt, token limit, context window, classification, sentiment, summarize, tldr, json mode, structured output, moderation, content policy, sub-agents, multi-agent, orchestration

Entry point: load this file for `ai`-related tasks. It enumerates available
skills, workflows, blueprints and validators for the AI capability.

Layout

- `memory/` — capability-local memories and proof bundles

Routing

1. Look for a blueprint in `.claude/blueprints/` (prefixed `ai-`).
2. Else, choose a workflow from `.claude/workflows/` (prefixed `ai-`).
3. Else, compose the `ai-` skills in the Skill tool list.

Always run `.claude/validators/` (prefixed `ai-`) before finalizing results: `ai-rag` routes through
`.claude/workflows/ai-rag.md`/`.claude/validators/ai-hallucination-check.md`; every other AI skill (`ai-model-router`,
`ai-text-classification`, `ai-summarization`, `ai-embeddings`, `ai-structured-output`,
`ai-moderation-filter`, `ai-agent-orchestrator`) routes through `.claude/validators/ai-output.md`.

Skills

The 9 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `ai-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `ai-agent-orchestrator`
- `ai-embeddings`
- `ai-hallucination-evaluator`
- `ai-model-router`
- `ai-moderation-filter`
- `ai-rag`
- `ai-structured-output`
- `ai-summarization`
- `ai-text-classification`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`ai-`. The copies still under `capabilities/ai/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `ai-rag`
- `.claude/validators/` — `ai-hallucination-check`, `ai-output`
- `.claude/workflows/` — `ai-rag`
