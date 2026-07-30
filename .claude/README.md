# .claude Directory — Conventions

Purpose: store capability packages, agents, MCP mappings and local conventions.
This directory is small and machine-readable; `CLAUDE.md` is the bootloader that
points to capability packages below.

Conventions

- Each capability is a self-contained package under `.claude/capabilities/<name>/`.
- Capability entry point: `index.md` (must be brief and list available artifacts).
- Prefer loading only the capability `index.md` and the minimal referenced files.
- Artifacts inside a capability:
  - `skills/` — small reusable skill implementations (prompts, scripts, adapters)
  - `workflows/` — orchestrated task graphs and pipelines
  - `blueprints/` — promoted, validated solution patterns
  - `validators/` — validators to run post-execution
  - `playbooks/` — human-run instructions and runbooks
  - `templates/` — code/infra templates
  - `memory/` — capability-local memory snippets and examples
  - `agents/` — specialized agent adapters and MCP mappings
  - `mcp/` — mappings to external MCPs (GitHub, Docker, Cloud)

Naming

- Use kebab-case for filenames: `oauth-workflow.md`.
- Keep each file focused and small. Prefer many small files to one large file.

Usage

1. Read `CLAUDE.md`.
2. Identify capability.
3. Load `.claude/capabilities/<capability>/index.md`.
4. Load only the referenced artifacts.

This README exists to help humans. The bootloader (`CLAUDE.md`) is the single
machine entry point.
