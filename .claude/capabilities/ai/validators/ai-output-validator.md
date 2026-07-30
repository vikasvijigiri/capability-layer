> **Superseded.** The canonical copy of this file is `.claude/validators/ai-output.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# AI Output Validator — ai/validators/ai-output-validator.md

Purpose: generic gate for AI skills that are not RAG-specific
(`model-router`, `text-classification`, `summarization`, `embeddings-skill`,
`structured-output`, `moderation-filter`, `agent-orchestrator`) before their
output is treated as final or persisted.

Checks

- Structured/JSON outputs conform to the declared schema
- Moderation/policy checks pass for user-facing content
- Classification/summarization outputs include a confidence or evidence trail
- Sub-agent orchestration outputs come from agents operating on disjoint files/contracts

Failure handling

- Mark output as `needs_review`
- Run `python tools/run_hook.py on-validate-fail --file payload.json` (payload: `{"validator": "ai-output-validator", "capability": "ai"}`)

On pass

- Run `python tools/run_hook.py on-artifact-create --file payload.json` if the output is persisted as an artifact.

Usage

Required gate for any AI skill without its own dedicated workflow/validator
(everything except `rag-skill`, which uses `rag-workflow`/`hallucination-check`).
