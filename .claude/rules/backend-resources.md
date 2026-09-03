---
paths:
  - "docs/plans/**/*.md"
  - "docs/specs/**/*.md"
  - ".claude/skills/engineering-standards/references/backend-standards.md"
---

# Backend engineering resources

When work touches backend design — API shape, data model, auth, scaling,
service boundaries — consult the highly-rated external references below
before deciding from the request text alone. They are references to read,
not dependencies: nothing here is vendored into this repo or installed as a
skill. Vetting (stars, last commit, license) is recorded in
`docs/research/2026-09-03-tech-resources.md`.

| Resource | Repo | What it gives you |
|---|---|---|
| System Design Primer | `donnemartin/system-design-primer` | Scalability, caching, load balancing, DB choice, queues — the vocabulary for a system-design decision |
| Microsoft REST API Guidelines | `microsoft/api-guidelines` | Concrete REST rules: versioning, pagination, error shape, naming, long-running operations |
| Node.js Best Practices | `goldbergyoni/nodebestpractices` | ~80 backend practices — project structure, error handling, security, production — Node-framed, mostly language-neutral |
| Google API Design Guide | `cloud.google.com/apis/design` (guide) | Resource-oriented API design, standard methods, a canonical error model |

- **This list is a floor, not a ceiling.** The ecosystem moves; also look
  for a more current or stronger backend reference at the time of the work
  and prefer it when you find one.
- **Ground, don't copy wholesale.** Use these to pick a direction or borrow
  a concrete pattern; the decision still lands in the plan or spec, and the
  procedure stays in
  `.claude/skills/engineering-standards/references/backend-standards.md`.

Per-language guides (Go, Rust, Python) are deliberately out of scope here —
this is the cross-cutting set.
