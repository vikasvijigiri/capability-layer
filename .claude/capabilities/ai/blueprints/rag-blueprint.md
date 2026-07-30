> **Superseded.** The canonical copy of this file is `.claude/blueprints/ai-rag.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# RAG Blueprint — ai/blueprints/rag-blueprint.md

Problem Signature

- Provide an explainable answer to a domain question using internal docs and external sources.

Solution Workflow

1. Retriever (vector DB) with `k=8`.
2. Evidence ranking and compression.
3. Generator with citation template.
4. Validators: `hallucination-check`, `citation-validator`.

Confidence: Medium-High
Reusability: High for document QA scenarios
