# Frontend Capability Package

Purpose: UI, UX, accessibility, component libraries, bundling and client-side
observability.

Keywords: frontend, ui, ux, accessibility, components, visual-testing, page, layout, css, styling, button, responsive, looks broken, design, screen, component, react, a11y, visual regression, screenshot diff, mobile, breakpoint, viewport, form, input, validation, user flow, journey, navigation, nav, wireframe, state management, client state, prop drilling, loading state, empty state, error state, re-render, figma, design token, modal, dropdown

Entry point: load this file only when the request belongs to the `frontend`
capability. It declares skills, workflows, blueprints, and validators specific
to frontend work.

Layout

- `index.md` — this file: the `Keywords:` line the router scans, plus the
  routing precedence a flat skill list cannot express. No other live content
  lives in this directory.
- `blueprints/`, `validators/`, `workflows/` — **superseded copies only.**
  Canonical versions are the top-level `.claude/` paths listed under Artefacts.

Routing

Prefer blueprints, then workflows, then skills. Run validators before release.

**`design-system` gates this entire capability.** It owns `DESIGN.md` — the token
table every `frontend-` skill generates and checks against. A project with no
`DESIGN.md` must run `design-system` before the first component is generated;
skipping it means components invent their own colour and spacing, which is the
one failure this capability exists to prevent. It is an unprefixed process skill
because it also serves non-frontend visual work, so a `frontend-` prefix scan
will not find it.

Order within the capability, when the work is a new feature rather than a fix:

1. `frontend-ux-flow` — which screens exist and how a user moves between them
2. `design-system` — tokens, if `DESIGN.md` does not exist yet
3. `frontend-state-architecture` — where state lives, fetching and caching policy
4. `frontend-component-generator` / `frontend-form-builder` — build against tokens
5. the audit skills below — accessibility, responsive, visual regression, bundle

Skills

The 8 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `frontend-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `frontend-ux-flow` — screens, navigation, dead-ends *(design)*
- `frontend-state-architecture` — state placement, fetching, async states *(design)*
- `frontend-component-generator` — scaffold a component *(build)*
- `frontend-form-builder` — fields, validation, submission *(build)*
- `frontend-accessibility-check` — axe violations *(audit)*
- `frontend-responsive-audit` — breakpoint breakage *(audit)*
- `frontend-visual-regression` — screenshot diff *(audit)*
- `frontend-bundling-helper` — bundle size *(audit)*

Plus `design-system` (unprefixed process skill) — see Routing above.

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`frontend-`. The copies still under `capabilities/frontend/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `frontend-component`
- `.claude/validators/` — `frontend-visual-diff`
- `.claude/workflows/` — `frontend-release`
