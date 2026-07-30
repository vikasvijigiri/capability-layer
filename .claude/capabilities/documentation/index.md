# Documentation Capability Package

Purpose: authoring, maintaining, and validating repository documentation,
APIs, and onboarding materials.

Keywords: documentation, docs, api, style, link-checks, readme, explain this repo, write docs, comment this, onboarding doc, changelog, doc this, release notes, adr, decision record, why did we choose

Entry point: load this file only for documentation-related tasks. It declares
skills, workflows and validators for content quality and consistency.

Layout


Routing

Prefer blueprints, then workflows, then skills. Run validators before merging
documentation changes.

Skills

The 5 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `documentation-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `documentation-adr-writer`
- `documentation-api-extractor`
- `documentation-changelog-generator`
- `documentation-doc-generator`
- `documentation-link-checker`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`documentation-`. The copies still under `capabilities/documentation/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `documentation-structure`
- `.claude/validators/` — `documentation-link-check`
- `.claude/workflows/` — `documentation-release`
