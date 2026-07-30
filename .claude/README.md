# .claude Directory — Conventions

Purpose: store skills, agents, artefacts, MCP mappings and local conventions.
This directory is small and machine-readable; `CLAUDE.md` is the bootloader.

Layout

Everything routable is a flat top-level directory, and the `<domain>-` name
prefix is what groups a file back to its capability. There is no per-capability
folder — `.claude/capabilities/` held one until 2026-07-31 and was removed once
its nine index files collapsed into `routing/capabilities.md`.

- `skills/<name>/SKILL.md` — the only shape the Skill tool discovers. A flat
  `.md`, or a frontmatter `name:` differing from the directory name, is silently
  invisible.
- `routing/capabilities.md` — the nine capabilities: keyword lists (scanned by
  `hooks/pre-run/02-capability-router.py`) and per-domain artefact pointers.
  Adding a `## <domain>` section here is the whole of adding a capability.
- `blueprints/`, `workflows/`, `validators/`, `playbooks/`, `templates/` —
  non-skill artefacts, named `<domain>-<name>.md`.
- `agents/` — repo-local subagent definitions.
- `hooks/<event>/` — lifecycle scripts. Registered in `settings.json`; also
  runnable via `tools/run_hook.py`.
- `mcps/` — MCP server reference docs. Not the live client config; that is
  `.mcp.json` at the repo root.
- `registry/` — **generated.** Run `tools/generate_registry.py`; never hand-edit.

Naming

- kebab-case filenames: `backend-oauth.md`.
- Capability skills are prefixed `<domain>-`; unprefixed names are cross-cutting
  process skills.
- Keep each file focused and small. Prefer many small files to one large file.

Usage

1. Read `CLAUDE.md`.
2. The router hook injects the capability keyword match on every prompt.
3. Invoke that domain's skills by name through the Skill tool.
4. Read the skill's own `## Routing` section for its mandatory validator and any
   blueprint or workflow that takes precedence.

This README exists to help humans. The bootloader (`CLAUDE.md`) is the single
machine entry point.
