---
name: documentation-api-extractor
model: sonnet
description: Extracts a structured API surface (functions, classes, endpoints, params) from source code for reference documentation. Use for "extract the API surface", "list all public endpoints", "generate an API reference", "what does this module expose", "list the public functions", "what endpoints exist", "pull out the api surface". Prefer this over reading the source by hand when the goal is a complete surface, not a spot answer. Do NOT use for full prose documentation — pair with doc-generator for that. Extraction only; for the narrative docs built on top, use the `technical-writer` agent.
effort: medium
---

# API Extractor Skill

Extracts a structured list of public functions/classes/endpoints and their signatures from source.

## When to use
- "extract the API surface", "list public endpoints", "API reference", "what does this module expose"

## Steps
1. Parse `source_code_path` for exported/public symbols.
2. Capture signature, params, return type, and doc-comment if present.
3. Return a structured `api_surface` list.

## Notes
Structured data only — feed into `doc-generator` for prose/markdown output.

## Routing

**Validator (required): `.claude/validators/documentation-link-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/documentation-structure.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/documentation-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
