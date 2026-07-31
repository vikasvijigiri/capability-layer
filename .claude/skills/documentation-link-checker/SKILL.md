---
name: documentation-link-checker
model: sonnet
disallowed-tools: Edit, Write, NotebookEdit
description: Crawls documentation files for broken internal/external links and reports them. Use for "check for broken links", "validate doc links", "link checker", "do these docs still point to the right files", "are these links still good", "the docs point at files that moved", "404s in the docs". Prefer this over clicking links manually - a moved file breaks silently and stays broken. Do NOT use for content/style review — that's a separate concern. Link validation only; it does not rewrite prose.
effort: medium
---

# Link Checker Skill

Crawls `doc_paths` for internal and external links and reports broken/stale ones.

## When to use
- "check for broken links", "validate doc links", "link checker"

## Steps
1. Extract all links from `doc_paths`.
2. Resolve internal links against the actual file tree; ping external links.
3. Classify each as OK / broken / redirected.
4. Return `link_report` with file:line for every broken link.

## Notes
Report only — does not auto-fix links; a human or follow-up edit fixes them.

## Routing

**Validator (required): `.claude/validators/documentation-link-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/documentation-structure.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/documentation-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
