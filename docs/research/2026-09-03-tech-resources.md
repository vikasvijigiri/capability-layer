# Tech-resource vetting — 2026-09-03

**Context:** `.claude/rules/*-resources.md` (backend, frontend, testing,
security, observability) each list highly-rated external repos an agent
consults before inventing practice. This is the vetting record required by
`capability-layer-maintenance` §2.

**Vetting floor:** an OSI/CC license, a push within ~12 months, and either a
large star count or canonical/official status (OWASP, Google SRE,
web.dev). 3–4 entries per domain — a short current list beats a long one
that rots. Facts pulled via the GitHub API (`search_repositories`),
2026-09-03; a `(guide)` row is a canonical non-repo reference.

## Backend

| Repo | Stars | Last push | License | What it gives you |
|---|---|---|---|---|
| `donnemartin/system-design-primer` | 367k | 2026-03-20 | CC-BY-4.0 (text) | Scalability, caching, load balancing, DB choice, queues — the vocabulary for a system-design decision |
| `microsoft/api-guidelines` | 23k | 2026-08-05 | CC-BY-4.0 | Concrete REST shape rules: versioning, pagination, errors, naming, long-running ops |
| `goldbergyoni/nodebestpractices` | 106k | 2026-06-15 | CC-BY-SA-4.0 | ~80 backend practices (project structure, error handling, security, production) — Node-framed, mostly language-neutral |
| Google API Design Guide (`cloud.google.com/apis/design`) | (guide) | — | CC-BY-4.0 | Resource-oriented API design, standard methods, error model |

- **Considered, not listed:** per-language backend guides (Go, Rust,
  Python) — deferred with the per-stack files the user scoped out.

## Frontend

| Repo | Stars | Last push | License | What it gives you |
|---|---|---|---|---|
| `alan2207/bulletproof-react` | 36k | 2026-05-14 | MIT | A worked, opinionated React architecture: feature folders, one-way deps, data-fetching, testing — the structure `frontend-standards.md` describes, in code |
| `airbnb/javascript` | 148k | 2026-04-16 | MIT | The JS style baseline most linters descend from; React and hooks sections |
| `thedaviddias/Front-End-Checklist` | 74k | 2026-08-14 | no explicit license — read-only | ~385 pre-ship checks across HTML, perf, a11y, SEO, security |
| web.dev (`web.dev`) | (guide) | — | Google, CC-BY-4.0 | Core Web Vitals definitions and the current perf/PWA/a11y guidance |

- **Considered, not listed:** `GoogleChrome/lighthouse` (a tool, not a
  practice guide — the running of it belongs in CI, cited from
  `performance-engineering.md`).

## Testing

| Repo | Stars | Last push | License | What it gives you |
|---|---|---|---|---|
| `goldbergyoni/javascript-testing-best-practices` | 25k | 2024-06-27 | MIT | 50+ practices: test anatomy, backend vs frontend, effectiveness measurement, CI — framework-agnostic reasoning |
| `testing-library/react-testing-library` | 20k | 2026-08-27 | MIT | The "test behaviour a user observes, not internals" model, and the API that enforces it |
| `goldbergyoni/nodejs-testing-best-practices` | 4.4k | 2026-02-10 | no explicit license — read-only | Component/integration testing with a real DB/queue, and an example app |
| Martin Fowler — Testing (`martinfowler.com/testing`) | (guide) | — | canonical | Test pyramid, test double taxonomy, contract testing — the definitions the field cites |

- **`goldbergyoni/javascript-testing-best-practices`** last pushed
  2024-06-27 — over the 12-month floor, kept for canonical status; re-check
  at use time and prefer a fresher equivalent if one exists.

## Security

| Repo | Stars | Last push | License | What it gives you |
|---|---|---|---|---|
| `OWASP/CheatSheetSeries` | 33k | 2026-09-02 | CC-BY-SA-4.0 | Concise per-topic secure-build guidance (authn, authz, injection, crypto, headers) — the builder's reference |
| `OWASP/ASVS` | 3.6k | 2026-09-03 | CC-BY-SA-4.0 | The Application Security Verification Standard — a levelled requirements checklist to test against |
| `OWASP/wstg` | 9.8k | 2026-09-03 | CC-BY-SA-4.0 | Web Security Testing Guide — how to actually probe each control |
| `shieldfy/API-Security-Checklist` | 23k | 2026-07-21 | MIT | Fast pre-release API security countermeasure list |
| `analysis-tools-dev/static-analysis` | 15k | 2026-08-30 | MIT | Curated SAST/linter tooling per language, to wire dependency+code scanning into CI |

- Pairs with `code-review/references/security-review.md` and
  `supply-chain-audit.md`, which own the in-repo procedure.

## Observability / SRE

| Repo | Stars | Last push | License | What it gives you |
|---|---|---|---|---|
| Google SRE books (`sre.google/books`) | (guide) | — | canonical | SLI/SLO/error-budget definitions, alerting philosophy, incident and postmortem practice |
| `open-telemetry/opentelemetry.io` | 960 | 2026-09-03 | CC-BY-4.0 | The vendor-neutral instrumentation standard docs — traces, metrics, logs, semantic conventions |
| `dastergon/awesome-sre` | 13k | 2025-08-28 | CC0-1.0 | Curated index into SRE books, articles, tools, newsletters |
| `adriannovegil/awesome-observability` | 660 | 2026-08-15 | CC0-1.0 | Curated index specific to metrics/logs/traces/visualisation tooling |

- **`dastergon/awesome-sre`** last pushed 2025-08-28 — ~12 months, kept as
  the canonical SRE index; re-check at use time.
- Pairs with `release-git/references/observability-sre.md`, which owns the
  in-repo readiness sequence.

### Common footer in every `*-resources.md`

- The list is a **floor, not a ceiling** — the ecosystem moves; look for a
  fresher/stronger equivalent at the time of the work.
- **Ground, don't copy wholesale** — borrow a direction or a concrete
  pattern; the owning skill/reference still holds the procedure.
- Nothing here is vendored or installed; these are references to read.
