---
name: documentation-changelog-generator
model: sonnet
description: Generates a CHANGELOG entry from a set of commits/PRs, grouped by change type (feat/fix/breaking). Use for "write the changelog", "generate release notes", "what changed in this release", "write the release notes", "summarise the last few PRs", "tell users what's new". Prefer this over pasting a commit log - grouping by change type is what makes it readable to a user. Do NOT use for full API documentation — that's doc-generator/api-extractor. Release notes only; for broader user-facing documentation use the `technical-writer` agent.
---

# Changelog Generator Skill

Groups commits/PRs by type (feat/fix/breaking/chore) and produces a versioned CHANGELOG entry.

## When to use
- "write the changelog", "generate release notes", "what changed in this release"

## Steps
1. Classify each entry in `commits_or_prs` by type.
2. Group and order (breaking first, then feat, then fix).
3. Return the `changelog_entry` for `version`.

## Notes
A breaking change must be called out explicitly, never buried under "fix".

## Routing

**Validator (required): `.claude/validators/documentation-link-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/documentation-structure.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/documentation-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
