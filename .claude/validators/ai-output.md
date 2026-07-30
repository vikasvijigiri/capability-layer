# AI Output Validator — .claude/validators/ai-output.md

Purpose: generic gate for AI skills that are not RAG-specific
(`ai-model-router`, `ai-text-classification`, `ai-summarization`, `ai-embeddings`,
`ai-structured-output`, `ai-moderation-filter`, `ai-agent-orchestrator`) before their
output is treated as final or persisted.

Checks

- Structured/JSON outputs conform to the declared schema
- Moderation/policy checks pass for user-facing content
- Classification/summarization outputs include a confidence or evidence trail
- Sub-agent orchestration outputs come from agents operating on disjoint files/contracts

Failure handling

- Mark output as `needs_review`
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "ai-output", "capability": "ai"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the output is persisted as an artifact.

Usage

Required gate for any AI skill without its own dedicated workflow/validator
(everything except `ai-rag`, which uses `.claude/workflows/ai-rag.md`/`.claude/validators/ai-hallucination-check.md`).
