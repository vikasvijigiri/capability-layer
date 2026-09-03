---
name: frontend-standards
description: Frontend code-level engineering — component architecture, state, data fetching, rendering architecture, rendering performance, type safety, error handling, security, testing, dependency governance. Read once `engineering-standards`' SCAN phase finds a frontend manifest. Visual/token/motion/accessibility-floor content is NOT here.
---

# Frontend standards

Code-level engineering only. Visual design — tokens, colour, type, motion,
layout, the accessibility floor — is `architecture/references/design-contract.md`'s
design contract; that file is cited here, never duplicated, so a visual
decision and a code decision are never edited in the same place for
different reasons. "Fast" and "modern-feeling" are produced by both files
together: this one controls what makes it fast and correct, the design
contract controls what makes it feel current. Neither alone is sufficient.
Vetted external frontend references: `.claude/rules/frontend-resources.md`.

## Component architecture

- Composition over configuration: small components combined, not one
  component with a growing prop list branching on booleans.
- A component that cannot be understood without reading its children's
  internals, or cannot change internals without breaking a consumer, has a
  boundary problem — the same test `architecture/SKILL.md` already applies
  to technical units generally.
- Colocate a component with its own styles and tests; keep cross-cutting
  concerns (auth, theming, routing) at the boundary, not threaded through
  every leaf.
- Default to server-renderable, dependency-free components; a component
  should need a client boundary because it holds interactive state or
  browser APIs, not by habit. See Rendering architecture below — this rule
  and that section are the same decision made twice if split apart.

### Project structure

- Organize by feature, not by file type — a `features/checkout/` directory
  holding its own components, hooks, api calls, and types beats a flat
  `components/`, `hooks/`, `api/` split where working on one feature means
  hunting across five folders. Reserve top-level `components/`, `hooks/`,
  `lib/`, `types/` for what's genuinely shared across features.
- Enforce a one-way dependency flow: shared code → features → app. Shared
  modules never import from a feature; features never import from another
  feature (compose multiple features together at the app/route layer
  instead); the app layer can import from both. This isn't a style
  preference — a codebase without this rule accretes silent coupling until
  no feature can be deleted or moved without breaking an unrelated one.
- Lint the boundary, don't rely on convention: a restricted-imports ESLint
  rule (or equivalent for your toolchain) that blocks `features/x`
  importing from `features/y`, and blocks `components/` or `hooks/`
  importing from `features/` or `app/`, turns this from a code-review
  nag into a build failure.
- Skip barrel files (`index.ts` re-exporting everything in a folder) for
  anything performance-sensitive — they defeat tree-shaking in several
  bundlers and can pull an entire feature's dependency graph into a route
  that only needed one component from it. Import directly from the file
  that defines what you need.

## State management

- Local state by default. Reach for a shared store only when two components
  that do not share a parent need the same value, or when prop-drilling
  crosses more than two or three levels.
- Server state (data fetched from an API) is not the same category as UI
  state (a modal being open) — mixing them in one store is the usual cause
  of stale-cache bugs that look like state-management bugs. Use a
  server-state library (e.g. a query cache) for the former, and keep it out
  of your global client store entirely.
- URL state (filters, tab selection, pagination) belongs in the URL, not in
  component or store state — it's the difference between a link that
  reproduces what the user saw and one that doesn't.
- Derive, don't duplicate: a value computable from existing state is a bug
  waiting to desync, not a new state variable.

## Data fetching

- Cache by default; treat every fetch as shared, not private to the
  component that triggered it, or two components fetching the same
  resource double the requests.
- Watch for request waterfalls — a fetch that only starts after another
  fetch's response arrives, when the two did not actually depend on each
  other. Fetch in parallel at the highest common ancestor, or hoist to the
  server render where the request can start before any client JS runs.
- Optimistic updates only with a real rollback path on failure — an
  optimistic update with no rollback is a UI that lies about what happened.
- Validate every response at the boundary (schema validation — e.g. zod,
  valibot, or equivalent), not just its TypeScript type. A type is a
  compile-time promise; the network doesn't keep promises. An API contract
  drifting silently past an unchecked `as Type` cast is a runtime bug
  wearing a type-safe costume.

## Rendering architecture

This is the primary lever for "fast" in a modern stack — get it wrong and
no amount of memoization or bundle-splitting downstream recovers the loss.

- Default to server rendering (RSC, SSR, or static generation) for content
  that doesn't need interactivity; ship a client component only for the
  subtree that actually holds state, handlers, or browser-only APIs. The
  question for every component is "does this need to run in the browser,"
  not "what did the last screen do."
- Stream the response (streaming SSR / progressive rendering) rather than
  blocking the full page on the slowest data dependency; show the shell
  immediately and resolve slow subtrees in place.
- Use Suspense boundaries at real loading-state seams — where a user
  meaningfully waits for something — not scattered defensively around
  every async call. Each boundary is a design decision about what the user
  sees while waiting, not a try/catch reflex.
- Hydration is a cost, not a given: for content-heavy, low-interactivity
  surfaces (marketing pages, articles, catalogs), consider islands or
  partial hydration over full-page client hydration. Measure
  time-to-interactive, not just time-to-first-byte, before deciding a page
  needs to be a full SPA route.
- State the rendering strategy per route or template explicitly (static /
  server-rendered / client-rendered, and why) — an undocumented default is
  how a static-eligible page ends up client-rendered by accident.
- Framework and rendering choice is downstream of the deploy target: on an
  edge runtime (e.g. Cloudflare Workers) there is no persistent Node
  process — confirm an edge-compatible build *before* committing to the
  framework, per `.claude/rules/edge-hosting.md`. A React Native /
  cross-platform target carries its own build and over-the-air-update
  constraints — `.claude/rules/mobile-app-builds.md`.

## Rendering performance

- Know what causes a re-render before reaching for memoization — memoizing
  a component that re-renders for a legitimate reason hides the cost
  without removing it.
- Bundle size: code-split by route at minimum, and by heavy/rare-use
  component (modals, editors, charts) beyond that; audit what a "just add
  a library" decision costs on the initial load, not just at review time.
- Budget against Core Web Vitals with numeric targets, not vibes: LCP
  (largest contentful paint) under ~2.5s, INP (interaction to next paint —
  replaced FID as the responsiveness metric in 2024; if a doc downstream
  still references FID, that's stale) under ~200ms, CLS (layout shift)
  under 0.1, all at the 75th percentile of real traffic, not lab-only.
  Enforce the budget in CI (Lighthouse CI or a bundle-size gate) — a
  budget with no gate is a wish.
- A performance claim needs a measurement (a profiler trace, a Lighthouse
  score, a bundle-analyzer diff, or field data against the budgets above)
  — the same evidence discipline this repository already applies
  everywhere else. Deeper method:
  `code-review/references/performance-engineering.md`.
- Images, fonts, and third-party scripts are usually the largest
  uncontrolled cost on a page — set an explicit policy (responsive
  images, font subsetting/preloading, third-party script budget and
  loading strategy) rather than leaving each addition to individual
  judgment at insert time.

## Type safety and contracts

- TypeScript strict mode (or equivalent) is the floor, not an aspiration —
  `any` and unchecked casts are a debt that compounds silently.
- Validate at every trust boundary: API responses, form input, URL params,
  environment variables. A type asserts a shape at compile time; a schema
  validator enforces it at runtime, at the one moment the shape can
  actually be wrong.
- Generate types from a single source of truth (OpenAPI spec, GraphQL
  schema, or the validation schema itself) rather than hand-maintaining a
  parallel type file that drifts from the contract it's supposed to mirror.

## Error handling

- Error boundaries at deliberate seams (route-level at minimum, plus
  around any subtree that fetches independently), each with a fallback
  that tells the user what to do next — not a blank screen or a generic
  "Something went wrong."
- Distinguish recoverable errors (retry, redirect, degrade gracefully)
  from fatal ones (surface clearly, report, stop) — treating every error
  the same is how a transient network blip and a broken build get the
  same, wrong, response.
- Every caught error is reported (to the monitoring pipeline in Production
  feedback loop below), not just swallowed locally — a try/catch with no
  report is a bug hidden from the people who'd fix it.

## Security

- Treat all rendered user content as untrusted by default; rely on the
  framework's escaping and avoid raw HTML injection (`dangerouslySetInnerHTML`
  or equivalent) unless the content is sanitized at the point of insertion,
  not assumed clean upstream.
- Set a Content-Security-Policy and review it when adding a new
  third-party script or embed — each addition is a new trust boundary,
  not a free insert.
- Never ship secrets, API keys, or internal endpoints into client-bundled
  code; if it's in the browser, it's public, regardless of how it's
  obfuscated.

## Testing

Component tests for behavior a user could observe (renders this, responds
to this interaction); integration tests across component boundaries for
real user flows; end-to-end sparingly, for the flows that must not break.
Mock the network boundary, not the component under test — a test that mocks
its own subject proves nothing.

- Test the rendering-architecture seams too: a Suspense fallback actually
  shows, an error boundary actually catches, streamed content resolves in
  the right order — these are behaviors a user observes and are as testable
  as a click handler.
- Vetted external testing references: `.claude/rules/testing-resources.md`.

## Dependency and bundle governance

- A bundle-size budget is enforced in CI, not just checked at review time
  for the one PR that happened to add a library — bloat is a series of
  small, individually-reasonable additions, not one big mistake.
- Every new dependency is evaluated against what it costs (bundle size,
  maintenance status, transitive dependencies) versus what a small amount
  of first-party code would cost instead — a dependency is a permanent
  liability, not a one-time convenience.
- Dependencies are updated on a deliberate cadence with a rollback plan,
  not left to drift until a security advisory forces an emergency bump.
  Supply-chain risk on a client dependency is its own attack surface —
  `code-review/references/supply-chain-audit.md`.

## Production feedback loop

- Real User Monitoring (RUM) tracks the Core Web Vitals budgets above
  against actual traffic, not just pre-ship lab measurement — a page that
  passes Lighthouse locally can still regress for real users on slow
  networks or low-end devices, and pre-ship measurement alone won't catch
  it.
- Alerts fire on regression against the budget, not just on hard failure
  — a page that's 40% slower than last month but still "working" is a
  problem this loop exists to catch before a user complaint does.
- Error tracking wiring: `.claude/rules/error-monitoring.md` names the
  free-tier default (Sentry, already an MCP entry in this layer) and its
  limits; `release-git/references/observability-sre.md` owns the generic
  logs/metrics/traces/alerts sequence — read it, don't restate it here.

## Where the visual contract lives

Color, type, spacing tokens, layout, motion, responsive states, and the
accessibility floor are `architecture/references/design-contract.md`'s
job, written as `DESIGN.md` for a given surface — as is the external
UI/UX resource list (`.claude/rules/ui-ux-resources.md`,
`.claude/rules/design-mcp.md`). This file points there **single-hop** and
does not cite those design rules directly. If a task needs both — a new
screen that also needs performant data fetching — read both files; this
one never restates the other's tokens or a11y rules.
