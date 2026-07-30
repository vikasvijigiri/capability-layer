---
name: stack-selector
model: opus
description: Picks an architecture pattern and a concrete free-tier/open-source stack, walking a fixed tie-break order, and records the decision as an ADR. Use for any "what stack should I use", "which framework", "which database", "which db", "how should we architect this" question — including one naming products directly ("postgres or mongo", "redis or not") — and before the first module of a new project is written. Prefer this over ad-hoc stack picking — an unrecorded stack choice becomes an unexplainable constraint later. Do NOT use for changes inside an already-chosen stack.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
provides: [architecture, stack, adr]
requires: [prd]
produces_artifact: false
retryable: true
---

# Stack Selector

Two decisions, in order: what architecture pattern fits the PRD, then which concrete
free-tier/open-source technologies implement it. Reusable standalone — any "what should
I build this with" question, not just inside `mvp-builder`.

## Steps

1. **Pick the architecture pattern** the PRD actually needs — a single deployable app is
   the default for an MVP; only reach for services/microservices if the PRD names
   something that genuinely requires independent scaling or deployment (per
   `engineering-policy`'s YAGNI — don't split what doesn't need splitting).
2. **Walk the Tie-Break Order**, top to bottom, first match wins — this is a fixed,
   already-made judgment call, not a runtime debate:
   1. Prefer one vendor covering frontend+backend+DB in a single free tier (Vercel,
      Railway, Render) over stitching three vendors together — fewer credentials,
      smaller leak surface.
   2. Prefer whatever this environment's own existing repos already lean on, if there's
      an established pattern to reuse — less novel failure surface.
   3. Prefer a signup path that requires **no credit card on file at all** over one that
      requires CC-with-nothing-charged — a CC requirement is itself a blocker for an
      autonomous run (see `deployment-pilot`), so avoiding it avoids an escalation, not
      just a cost.
   4. Prefer a vendor with a scriptable CLI (`vercel`, `netlify`, `flyctl`, `railway`)
      over console-only click-through — an autonomous run has no one to click a
      dashboard.
   5. Final tie-break, fixed order: Vercel > Netlify > Railway > Render > Fly.io >
      Cloudflare Pages.
3. **Respect all free-tier quotas, not just billing dollars** — CI/build minutes,
   storage, and DB row/request quotas are also part of the zero-cost ceiling
   (`engineering-policy`); note the specific quota you're relying on in the ADR so a
   later `error-recovery` incident referencing "this host's free tier silently caps X"
   has something concrete to check against.
3a. **If the PRD needs auth, email, or payments, pick a free-tier provider for those
   too** — don't leave them undecided just because the Tie-Break Order above is about
   hosting. Defaults: auth — the host's bundled option if it has one (e.g. Supabase
   Auth), else Clerk/Auth0 free tier; transactional email — Resend or SendGrid free
   tier; payments — Stripe test mode (never live keys in an autonomous run; a request
   for real payment processing is a `deployment-pilot` must-supply-credential blocker,
   not something to wire up unattended). Record whichever was picked in the same ADR.
4. **Write the ADR** to `decisions/` (the lightweight
   Decision/Why/Alternatives-considered shape in `knowledge-manager`'s `formats.md`): the architecture pattern, the concrete
   stack, and which tie-break rule decided it.

## Relationship to other skills

- Consumes `requirements-analyst`'s PRD; never re-derives requirements.
- `repo-onboarding` records this decision into the repo's `CLAUDE.md` "Detected stack"
  section rather than re-deriving the stack independently — this skill is the one
  source of truth for what was chosen and why.
- `code-review`'s architecture-drift check compares later diffs against this ADR —
  write it concretely enough to be checked against, not just narratively.

## Note on project-local overrides

A repo can have its own `.claude/skills/stack-selector/` with a repo-tailored version
(e.g. a mandated vendor instead of the free-tier Tie-Break Order — a company policy
requiring AWS, say). Where both exist, the project-local one takes precedence for that
repo — this global version is the default otherwise.
