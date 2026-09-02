---
paths:
  - "DESIGN.md"
  - "docs/specs/**/*.md"
---

# UI/UX design resources

When work touches a user-facing surface — choosing layout, colour, type,
spacing, motion, component states, or judging whether a UI reads as
generic "AI slop" — consult the external design-intelligence projects
below before inventing values from the request text alone. They are
references to read, not dependencies: nothing here is vendored into this
repo or installed as a skill, and each is MIT-licensed.

| Resource | Repo | What it gives you |
|---|---|---|
| UI UX Pro Max | `nextlevelbuilder/ui-ux-pro-max-skill` | Searchable databases — UI styles, colour palettes, font pairings, per-industry reasoning rules, UX guidelines, motion and chart presets |
| Taste Skill | `Leonxlnx/taste-skill` | Anti-"AI slop" frontend taste — stronger layout, typography, motion and spacing, a built-in critique pass, and parameterised style variants |
| Awesome Claude Design | `VoltAgent/awesome-claude-design` | Ready-to-use design systems in `DESIGN.md` format — adopt one so later screens stay on-brand automatically |

- **This list is a floor, not a ceiling.** The Claude-design ecosystem
  moves fast and these repos change. Also look for current UI/UX skills,
  design-system collections, and taste references at the time of the
  work, and prefer a better or more current one when you find it.
- **Ground, don't copy wholesale.** Use these to pick a direction and to
  borrow concrete tokens or patterns; the surface's own contract still
  lives in `DESIGN.md`, and a linked Figma file still wins — see
  `.claude/rules/design-mcp.md`.

The owning procedure and platform-specific guidance are in
`.claude/skills/architecture/references/design-contract.md` and
`.claude/skills/architecture/references/platform-guidance.md`.
