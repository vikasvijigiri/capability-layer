---
paths:
  - "docs/plans/**/*.md"
  - "docs/specs/**/*.md"
  - ".claude/skills/engineering-standards/references/backend-standards.md"
  - ".claude/skills/engineering-standards/references/frontend-standards.md"
---

# Testing resources

When work defines a test strategy — what to test at which level, how to
structure a suite, what to mock — consult the highly-rated external
references below before deciding from the request text alone. They are
references to read, not dependencies: nothing here is vendored into this
repo or installed as a skill. Vetting (stars, last commit, license) is
recorded in `docs/research/2026-09-03-tech-resources.md`.

| Resource | Repo | What it gives you |
|---|---|---|
| JavaScript Testing Best Practices | `goldbergyoni/javascript-testing-best-practices` | 50+ practices — test anatomy, backend vs frontend, effectiveness measurement, CI — framework-agnostic reasoning |
| React Testing Library | `testing-library/react-testing-library` | The "test behaviour a user observes, not internals" model and the API that enforces it |
| Node.js Testing Best Practices | `goldbergyoni/nodejs-testing-best-practices` | Component / integration testing against a real DB or queue, with an example app |
| Martin Fowler — Testing | `martinfowler.com/testing` (guide) | Test pyramid, test-double taxonomy, contract testing — the definitions the field cites |

- **This list is a floor, not a ceiling.** Some entries lag their field;
  re-check at the time of the work and prefer a fresher equivalent when one
  exists.
- **Ground, don't copy wholesale.** Use these to pick proportions and
  patterns; the per-domain testing guidance stays in
  `.claude/skills/engineering-standards/references/backend-standards.md` and
  `.claude/skills/engineering-standards/references/frontend-standards.md`.

Framework-specific runners (Jest, Vitest, Playwright, pytest) are a target-
repo choice, detected by `engineering-standards`' SCAN, not fixed here.
