---
name: research-papers-extraction
model: opus
description: Extracts structured metadata (title, authors, abstract, key findings) from academic papers or long-form articles. Use for "summarize this paper", "extract findings from this article", "what does this paper claim", "literature review input", "what does this paper say", "summarise this study", "pull the findings out of this", "what did they actually measure". Prefer this over reading the abstract alone - the abstract routinely overstates the result. Do NOT use for casual blog posts with no formal claims to extract. Gathers evidence only; it does not decide — a decision reached this way still needs recording via `knowledge-manager`.
effort: high
---

# Papers Extraction Skill

Extracts structured metadata and key findings from an academic paper or long-form article.

## When to use
- "summarize this paper", "extract findings", "what does this paper claim", "literature review input"

## Steps
1. Parse `document_source` for title/authors/abstract.
2. Extract key claims/findings and methodology notes.
3. Return a structured `paper_summary`.

## Notes
Distinguish the paper's own claims from your interpretation — never blend the two.

## Routing

**Validator (required): `.claude/validators/research-citation-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.
