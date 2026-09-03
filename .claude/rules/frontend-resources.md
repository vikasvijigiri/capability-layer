---
paths:
  - "docs/plans/**/*.md"
  - "docs/specs/**/*.md"
  - ".claude/skills/engineering-standards/references/frontend-standards.md"
---

# Frontend engineering resources

When work touches frontend code — component architecture, project
structure, rendering strategy, state, performance — consult the
highly-rated external references below before deciding from the request
text alone. They are references to read, not dependencies: nothing here is
vendored into this repo or installed as a skill. Vetting (stars, last
commit, license) is recorded in
`docs/research/2026-09-03-tech-resources.md`.

| Resource | Repo | What it gives you |
|---|---|---|
| Bulletproof React | `alan2207/bulletproof-react` | A worked, opinionated React architecture — feature folders, one-way deps, data fetching, testing — the structure in code |
| Airbnb JavaScript Style Guide | `airbnb/javascript` | The JS/React style baseline most linters descend from |
| Front-End Checklist | `thedaviddias/Front-End-Checklist` | ~385 pre-ship checks across HTML, performance, accessibility, SEO, security |
| web.dev | `web.dev` (guide) | Core Web Vitals definitions and current performance / PWA / accessibility guidance |

- **This list is a floor, not a ceiling.** The ecosystem moves fast; also
  look for a more current or stronger frontend reference at the time of the
  work and prefer it when you find one.
- **Ground, don't copy wholesale.** Use these to pick a direction or borrow
  a concrete pattern; the procedure stays in
  `.claude/skills/engineering-standards/references/frontend-standards.md`,
  and visual/token/motion decisions stay in `.claude/rules/ui-ux-resources.md`.

Per-framework guides beyond React are deliberately out of scope here — this
is the cross-cutting set.
