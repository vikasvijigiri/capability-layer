> **Superseded.** The canonical copy of this file is `.claude/workflows/ai-rag.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# RAG Workflow — ai/workflows/rag-workflow.md

Purpose: full RAG pipeline orchestration with validators and evidence collection.

Stages

1. Retrieve: call `rag-skill` retriever.
2. Generate: call generator with ranked context.
3. Validate: run `hallucination-check` and `citation-validator`.
4. Reflect: store evidence and candidate improvements if validation flags issues.

Safety

- Mark answers as "needs review" if validation fails.
- Do not perform side-effects based on unvalidated outputs.
