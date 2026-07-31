---
name: ai-rag
model: sonnet
description: Assembles a retrieval-augmented-generation pipeline (retrieve, rank, generate, cite) without side-effects. Use for "RAG", "retrieval augmented", "answer with citations", "search my docs and answer", "hallucination check on an answer", "answer questions over my own docs", "make it cite where it got that", "it keeps making things up", "search my files and answer". Prefer this over hand-rolling a retrieval loop - grounding and citation are the parts that get skipped. Do NOT use for raw prompt engineering with no retrieval step. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
effort: medium
---

# RAG Skill

Retrieves top-k evidence, compresses it, and generates a cited answer. Pure pipeline — no side effects.

## When to use
- "RAG", "retrieval augmented generation", "answer using our docs/knowledge base"
- "why did the model hallucinate", "add citations to this answer"

## Steps
1. Retrieve top-k documents via `retriever_config`.
2. Compress and rank evidence snippets.
3. Generate with compressed context + prompt template.
4. Return `answer` + `evidence_snippets` + citations.

## Notes
Keep retrieval and generation decoupled. Run hallucination + citation validators before returning the answer as final.

## Routing

**Validator (required): `.claude/validators/ai-hallucination-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/ai-rag.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
