# Release Workflow — .claude/workflows/frontend-release.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: orchestrate frontend release: build, test, visual-check, and promote.

Stages

1. Build: run bundler and unit tests.
2. Visual Test: run .claude/validators/frontend-visual-diff.md validator.
3. Accessibility: run `accessibility-check`.
4. Smoke: run basic smoke tests.
5. Promote: tag release and publish.

Validators

- Visual diff
- Accessibility

Safety

- Fail fast on visual diffs or major accessibility regressions.
