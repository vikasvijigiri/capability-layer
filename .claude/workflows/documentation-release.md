# Doc Release Workflow — .claude/workflows/documentation-release.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: review and publish documentation changes.

Stages

1. Generate docs via `doc-generator`.
2. Run .claude/validators/documentation-link-check.md and spellcheck.
3. Human review and merge.
4. Publish to docs site.

Validators

- Link-check
- Style guide compliance

Safety

- Do not auto-merge generated docs without human approval.
