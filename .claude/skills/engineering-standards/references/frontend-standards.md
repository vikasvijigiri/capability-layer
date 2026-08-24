---
name: frontend-standards
description: Frontend code-level engineering — component architecture, state, data fetching, rendering performance, testing. Read once `engineering-standards`' SCAN phase finds a frontend manifest. Visual/token/motion/accessibility-floor content is NOT here.
---

# Frontend standards

Code-level engineering only. Visual design — tokens, colour, type, motion,
layout, the accessibility floor — is
`architecture/references/design-contract.md`'s design contract; that file
is cited here, never duplicated, so a visual decision and a code decision
are never edited in the same place for different reasons.

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

## State management

- Local state by default. Reach for a shared store only when two components
  that do not share a parent need the same value, or when prop-drilling
  crosses more than two or three levels.
- Server state (data fetched from an API) is not the same category as UI
  state (a modal being open) — mixing them in one store is the usual cause
  of stale-cache bugs that look like state-management bugs.

## Data fetching

- Cache by default; treat every fetch as shared, not private to the
  component that triggered it, or two components fetching the same
  resource double the requests.
- Watch for request waterfalls — a fetch that only starts after another
  fetch's response arrives, when the two did not actually depend on each
  other.
- Optimistic updates only with a real rollback path on failure — an
  optimistic update with no rollback is a UI that lies about what happened.

## Rendering performance

- Know what causes a re-render before reaching for memoization — memoizing
  a component that re-renders for a legitimate reason hides the cost
  without removing it.
- Bundle size: code-split by route at minimum; audit what a "just add a
  library" decision costs on the initial load, not just at review time.
- A performance claim needs a measurement (a profiler trace, a Lighthouse
  score, a bundle-analyzer diff) — the same evidence discipline this
  repository already applies everywhere else.

## Testing

Component tests for behavior a user could observe (renders this, responds
to this interaction); integration tests across component boundaries for
real user flows; end-to-end sparingly, for the flows that must not break.
Mock the network boundary, not the component under test — a test that mocks
its own subject proves nothing.

## Where the visual contract lives

Color, type, spacing tokens, layout, motion, responsive states, and the
accessibility floor are `architecture/references/design-contract.md`'s job,
written as `DESIGN.md` for a given surface. If a task needs both — a new
screen that also needs performant data fetching — read both files; this one
never restates the other's tokens or a11y rules.
