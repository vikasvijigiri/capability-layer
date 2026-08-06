
# docs/ Structure and Usage

This rule documents the project policy for the `docs/` directory and when to
create subfolders under it. It loads every session and applies as a standing
constraint for contributors and automated scaffolding.

- Keep a single `docs/` root at the repository top for general project
  documentation and shared artefacts (plans, architecture, governance).
- Do not create empty or speculative subfolders under `docs/`.
- Create a subfolder when you have a distinct content category with at least
  one substantive page (e.g. `docs/plans/`, `docs/archive/`, `docs/api/`).
- Prefer flat structure: `docs/<category>/` is enough. Deep nesting (`docs/a/b/c`)
  is discouraged unless the documentation itself is large and logically
  partitioned.
- Use `docs/plans/` for active delivery plans and `docs/archive/` for retired
  content; prefer `decisions/` for design decisions rather than burying them
  inside deep docs paths.
- Update `CLAUDE.md` and `.claude/rules/` when you add or remove a docs
  category so the rule stays synchronized with the actual repo structure.
---

# How to apply

- The SessionStart bootstrap loader should create `docs/` root and only the
  shallow category folders that are actively used (or their README placeholders
  when justified), not several speculative empty trees.
- When in doubt, keep the docs root only and add a README explaining the
  proposed structure — the presence of a README is a stronger signal than an
  empty folder.
