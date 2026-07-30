# Requirements Analyst

Turns a goal/objectives/deliverables statement into a PRD, an MVP-cut feature list, and
per-feature acceptance criteria. Owns the **Scope-Cut Defaults** — the rules for
resolving an ambiguous requirement without asking (read-only over read-write,
single-user over multi-tenant, sync over async, happy-path over broad edge-case
coverage, seed data over an admin UI) — every cut gets recorded, never applied
silently.

Reusable standalone, not just inside `mvp-builder`: any "turn this vague idea into a
concrete spec" request fits this skill.

See [`SKILL.md`](SKILL.md) for the exact steps and how its output (the PRD and
acceptance criteria) is consumed downstream by `stack-selector` and `code-review`.
