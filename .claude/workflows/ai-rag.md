# RAG Workflow — .claude/workflows/ai-rag.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: full RAG pipeline orchestration with validators and evidence collection.

Stages

1. Retrieve: call `ai-rag` retriever.
2. Generate: call generator with ranked context.
3. Validate: run `.claude/validators/ai-hallucination-check.md` and `citation-validator`.
4. Reflect: store evidence and candidate improvements if validation flags issues.

Safety

- Mark answers as "needs review" if validation fails.
- Do not perform side-effects based on unvalidated outputs.
