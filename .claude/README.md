# .claude Directory — Conventions

Purpose: store skills, hooks, routing and local conventions. This directory is
small and machine-readable; `CLAUDE.md` is the bootloader.

**State: mid-rebuild.** The capability layer was torn down on 2026-08-01 —
agents, blueprints, workflows, validators, playbooks, templates, MCP docs, the
generated registries and the nine-domain capability routing are all gone, along
with 85 of the 87 skills. Recover any of it from commit `eaab430`. What follows
describes what is actually here.

Layout

- `skills/<name>/SKILL.md` — the only shape the Skill tool discovers. A flat
  `.md`, or a frontmatter `name:` differing from the directory name, is silently
  invisible. Two skills: `brainstormer` and `writing-plans`.
- `routing/process-skills.md` — keyword → skill-name routing, scanned by
  `hooks/pre-run/05-process-skill-router.py` on every prompt. The only routing
  signal that survives skill-listing truncation, so every skill needs an entry.
- `hooks/<event>/` — lifecycle scripts. Registered in `settings.json`, which is
  what actually fires them; `hooks/hooks_registry.json` documents intent only.
  Also runnable via `tools/run_hook.py`.
- `commands/` — `/verify`, `/save`, `/wip`, `/skills-doctor`.

Naming

- kebab-case directory names, matching the skill's frontmatter `name:` exactly.
- Keep each file focused and small. Prefer many small files to one large file.

Usage

1. Read `CLAUDE.md`.
2. The process-skill router injects any keyword match on every prompt.
3. Invoke the named skill through the Skill tool.
4. Read the skill's own `## Routing` section for its gate and terminal handoff.

This README exists to help humans. The bootloader (`CLAUDE.md`) is the single
machine entry point.
