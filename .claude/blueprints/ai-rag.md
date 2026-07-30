# RAG Blueprint — .claude/blueprints/ai-rag.md

Problem Signature

- Provide an explainable answer to a domain question using internal docs and external sources.

Solution Workflow

1. Retriever (vector DB) with `k=8`.
2. Evidence ranking and compression.
3. Generator with citation template.
4. Validators: `.claude/validators/ai-hallucination-check.md`, `citation-validator`.

Confidence: Medium-High
Reusability: High for document QA scenarios
