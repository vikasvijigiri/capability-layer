> **Superseded.** The canonical copy of this file is `.claude/workflows/frontend-release.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Release Workflow — frontend/workflows/release-workflow.md

Purpose: orchestrate frontend release: build, test, visual-check, and promote.

Stages

1. Build: run bundler and unit tests.
2. Visual Test: run visual-diff validator.
3. Accessibility: run `accessibility-check`.
4. Smoke: run basic smoke tests.
5. Promote: tag release and publish.

Validators

- Visual diff
- Accessibility

Safety

- Fail fast on visual diffs or major accessibility regressions.
