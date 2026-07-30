---
name: ai-embeddings
model: sonnet
description: Generates and manages text embeddings for semantic search, clustering, or similarity scoring, including vector-store upsert plans. Use for "embed this", "semantic search over these docs", "find similar items", "cluster these texts", "set up a vector store", "find similar ones", "search by meaning not exact words", "group these together", "match on intent". Prefer this over keyword search when the user describes matching by meaning rather than exact text. Do NOT use for keyword/exact-match search — that's a simpler grep/index problem. Implementation-level; for choosing models, providers or the overall AI architecture, use `stack-selector`.
---

# Embeddings Skill

Chunks documents, generates embeddings, and produces an upsert plan for a target vector store.

## When to use
- "embed this", "semantic search", "find similar items", "cluster these texts", "set up a vector store"

## Steps
1. Chunk `documents` at a size appropriate to `embedding_model`'s context window.
2. Generate embeddings per chunk.
3. Produce an upsert plan (ids, metadata, vectors) for `vector_store_target`.
4. Return `plan` + a sample similarity query to validate retrieval quality.

## Notes
Chunking strategy drives retrieval quality more than the model choice — validate with a sample query before bulk upsert.

## Routing

**Validator (required): `.claude/validators/ai-output.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/ai-rag.md` - a matching blueprint takes precedence over a hand-built solution.
