> **Superseded.** The canonical copy of this file is `.claude/workflows/documentation-release.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Doc Release Workflow — documentation/workflows/doc-release.md

Purpose: review and publish documentation changes.

Stages

1. Generate docs via `doc-generator`.
2. Run link-check and spellcheck.
3. Human review and merge.
4. Publish to docs site.

Validators

- Link-check
- Style guide compliance

Safety

- Do not auto-merge generated docs without human approval.
