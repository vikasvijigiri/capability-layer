---
name: backend-standards
description: Backend decision matrix and checklist — API design, auth, data, security, testing, deployment, observability. Read once `engineering-standards`' SCAN phase finds a backend manifest.
---

# Backend standards

Decision matrices and checklists, not prose essays — apply them to whatever
stack SCAN found, never to a hypothetical one.

## Technology decision matrix

| Need | Choose |
|---|---|
| Fast iteration, full-stack team | Node.js + a batteries-included framework |
| Data/ML integration | Python + an async framework |
| High concurrency, low memory | Go |
| Maximum raw performance | Rust |
| ACID transactions, relational data | PostgreSQL |
| Flexible/evolving schema | MongoDB or another document store |
| Caching, session state, rate limiting | Redis |
| Internal service-to-service calls | gRPC |
| Public API, broad client compatibility | REST |
| Client-driven, varied query shapes | GraphQL |

## API design

- **REST** when the client set is broad and uncontrolled, resources map
  cleanly to nouns, and HTTP caching semantics are useful as-is.
- **GraphQL** when clients need different shapes of the same data and
  over/under-fetching is a real cost — pair with query complexity limits, or
  a client gets to name its own N+1.
- **gRPC** for internal service-to-service calls where the two ends can
  agree on a schema and deploy together; not for a public API a third party
  integrates against without your SDK.
- Version explicitly (URL or header), document the deprecation window
  before shipping v1, and never silently break a response shape.

## Auth

- OAuth 2.1 + PKCE for anything with a browser or mobile client in the loop.
- JWTs for stateless service-to-service auth; short expiry, refresh
  rotation, and a real revocation path — a JWT with no revocation path is a
  credential that outlives the incident that should have killed it.
- Session cookies (httpOnly, secure, sameSite) remain the right default for
  a first-party web app with no cross-service auth need — token auth is not
  automatically the modern choice.

## Security — OWASP Top 10, as a checklist, not a paragraph

- Parameterized queries or an ORM that never string-concatenates SQL.
- Password hashing: Argon2id (or bcrypt if the runtime lacks it) — never a
  fast general-purpose hash.
- Input validation at the boundary, not deep inside business logic.
- Rate limiting on auth and any expensive endpoint.
- Security headers: CSP, HSTS, X-Content-Type-Options, a locked-down CORS
  allowlist — never `*` with credentials.
- Dependency scanning wired into CI, not a one-time audit.
- Secrets from environment/secret manager, never committed — matches this
  repo's own `Never: Commit secrets or credentials.`

## Testing — proportions, not absolutes

Roughly 70% unit (fast, isolated, the bulk of coverage), 20% integration
(real DB/queue, boundary-crossing), 10% end-to-end (the full stack, slow,
reserved for the paths that actually matter). Add contract tests at every
service boundary in a microservice architecture — a passing unit suite on
both sides of a broken contract is the failure this class of test exists to
catch.

## Deployment

Blue-green or canary over in-place deploys — a bad release should be a
traffic-shift away from rollback, not a redeploy. Feature flags decouple
deploy from release. Health/readiness checks that verify real dependencies
(DB reachable, not just "process is up") — a health check that lies is worse
than none, per `release-git/references/observability-sre.md`'s anti-patterns.

## Observability

`release-git/references/observability-sre.md` already owns the generic
readiness sequence (SLIs/SLOs, structured logs, metrics, traces, alerts,
dashboards) — read it, don't restate it here. The standard tool pairing for
metrics/dashboards/alerts is Prometheus + Grafana, with OpenTelemetry for
traces. `grafana/mcp-grafana` is the real, official Grafana MCP server
(confirmed present and maintained as of this writing) — wiring it live into
`release-git` is named follow-on work in this feature's plan, not built yet;
until it is, treat Grafana/Prometheus as the recommended default to name in
a design or incident writeup, not as a tool this skill can call.
