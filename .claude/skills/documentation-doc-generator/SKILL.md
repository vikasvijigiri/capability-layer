---
name: documentation-doc-generator
model: sonnet
description: Extracts a public API surface from source code and generates documentation skeletons. Use for "generate docs for this", "document this API", "create a README skeleton", "onboarding doc for this module", "nobody knows how to use this", "write some docs for it", "we need a readme for this module", "how do people get started with it". Prefer this over ad-hoc prose - an extracted surface keeps the docs honest about what actually exists. Do NOT use for prose/tutorial writing with no API surface to extract. For user-facing API/module docs; this repo's own CLAUDE.md is owned by `repo-onboarding`, and TASK/PLAN/HANDOFF/LOG/ISSUES by `knowledge-manager`.
effort: medium
---

# Doc Generator Skill

Parses source for public API definitions and generates markdown documentation skeletons.

## When to use
- "generate docs", "document this API", "README skeleton", "onboarding doc for this module"

## Steps
1. Parse `source_code_path` for public API definitions.
2. Generate markdown skeletons in `doc_style`.
3. Run link and lint checks.
4. Return `generated_docs` + `todo_items` for anything under-specified.

## Notes
Generated docs must be human-reviewed before merging — this skill never merges its own output.

## Routing

**Validator (required): `.claude/validators/documentation-link-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/documentation-structure.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/documentation-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
