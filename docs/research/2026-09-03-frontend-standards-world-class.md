# Frontend-standards world-class grounding — 2026-09-03

**Context:** `references/frontend-standards.md` was rewritten from a 5-section
code-level sketch to a fuller reference. `capability-layer-maintenance` §2
requires a request framed as "world class" to record what the result is
grounded in and what was deliberately left out. This is that record — a
grounding note, not a fresh external audit; re-check framework-specific
specifics against the target repo's actual stack at use time (the skill's SCAN
phase already mandates this).

## Primary sources the content is grounded in

| Topic | Source | What it anchors |
|---|---|---|
| Loading performance | web.dev — Core Web Vitals | LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1 at p75; INP replaced FID in 2024 |
| Field vs lab | web.dev — CrUX / RUM guidance | "passes Lighthouse locally, regresses in the field" — the Production feedback loop section |
| DOM injection | OWASP — DOM-based XSS / Cross-Site Scripting Prevention Cheat Sheet | `dangerouslySetInnerHTML`-class sinks, escape-by-default binding, CSP |
| Dependency risk | OWASP — Vulnerable and Outdated Components (A06) | deliberate update cadence + rollback; cross-ref `code-review/references/supply-chain-audit.md` |
| Rendering model | React docs — Server Components / Suspense / streaming | server-default, client boundary only where state/handlers/browser APIs live |
| Schema-at-boundary | Common practice (zod / valibot / OpenAPI codegen) | "a type is a compile-time promise; the network doesn't keep promises" |

## How a real published skill scopes frontend practice

The prior UI/UX research cycle (see
`decisions/2026-08-31-knowledge-skills-consulted-not-staged.md` and the
`docs/research/2026-08-19-*` comparison) already established the shape this
layer follows: a single hub skill with stack detection plus `references/*.md`
depth (as `AThevon/genjutsu` does), not many overlapping top-level skills, and
a hard split between **code-level** engineering and the **visual** design
contract. This rewrite stays inside that established shape.

## Adopted here / left to design-contract.md / out of scope

| Area | Disposition |
|---|---|
| Rendering architecture, Core Web Vitals budgets, type-at-boundary, error boundaries, dependency governance, RUM | **Adopted** into `frontend-standards.md` — all code-level |
| Feature-based project structure + one-way dependency flow + lint-enforced boundary | **Adopted** — architectural, not visual |
| Colour / type / spacing tokens, motion, layout, responsive states, visual accessibility floor (contrast, target size, reduced-motion) | **Left to** `architecture/references/design-contract.md` — the enforced boundary; `frontend-standards.md` points single-hop |
| External UI/UX resource databases (`ui-ux-resources.md`, `design-mcp.md`) | **Left to** `design-contract.md`, which already owns them; not cited directly from `frontend-standards.md` |
| Hosting / BaaS / error-monitoring vendor defaults and free-tier limits | **Left to** `.claude/rules/{edge-hosting,backend-baas,error-monitoring,mobile-app-builds}.md`; the reference files point at them, never restate the limits |
| Framework-specific API detail (exact Next.js / Remix / SvelteKit config) | **Out of scope** — the skill SCANs the target repo's actual stack; a reference file that hard-codes one framework's API drifts |

## Follow-up

- If `frontend-standards.md` grows past ~240 lines again, split it into
  `references/frontend/*.md` topic files with a navigation table in `SKILL.md`
  (the split-into-files option was deferred on this branch —
  `docs/engineering-standards-frontend-depth`).
