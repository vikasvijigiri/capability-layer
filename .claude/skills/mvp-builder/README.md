# MVP Builder

The user-invocable entry point for a fully autonomous, zero-checkpoint MVP build. Takes
a goal/objectives/deliverables statement once, confirms it as a structured brief (the
one deliberate human moment in the whole run), then hands off to
[`.claude/workflows/build-mvp.js`](../../workflows/build-mvp.js) via the `Workflow`
tool.

Deliberately thin: this skill does not implement, review, deploy, or record anything
itself — every phase of the actual build lives in `build-mvp.js` and the skills it
dispatches to (`requirements-analyst`, `stack-selector`, `repo-onboarding`, `code-review`,
`no-slop-check`, `deployment-pilot`, `error-recovery`, `knowledge-manager`). Splitting it
this way keeps the one user-invocable trigger simple and lets the orchestration logic
live in one script instead of being smeared across a skill file.

See [`SKILL.md`](SKILL.md) for the exact steps, the `## Autonomy Mode` override (what
"zero interference" does and does not supersede), and the workspace-isolation
(`~/mvp-builds/<slug>/`) convention that also lets `git_delivery_guard.py` recognize an
autonomous-build repo.
