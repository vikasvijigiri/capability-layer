---
name: observability-sre
description: Design or audit production signals - logs, metrics, traces, SLOs, alerts, dashboards, health checks, runbooks, capacity, rollback evidence. Before launch, after incidents, or when a service cannot be operated confidently. Do NOT use logs alone as observability, or create an alert with no action.
when_to_use: when a service needs production signals, SLOs, alerts, or operational readiness
effort: high
model: sonnet
disable-model-invocation: false
---

# Observability and SRE

Design observability around decisions an operator must make, not around every
line of code.

## Readiness sequence

1. Define critical user journeys, service boundaries, dependencies, and failure
   modes. Choose a small set of service and journey-level indicators.
2. Define SLI/SLO targets and error budgets with windows, ownership, and what
   happens when the budget is exhausted.
3. Add structured logs with correlation/request IDs, useful dimensions, safe
   redaction, and actionable error context. Never log credentials or raw
   sensitive payloads.
4. Add metrics for rate, errors, duration, saturation, queue depth, dependency
   health, and resource limits. Add traces across important boundaries.
5. Create alerts only for actionable symptoms. Each alert needs severity,
   owner, runbook, deduplication, and a tested escalation path.
6. Verify dashboards, health/readiness checks, smoke tests, rollback, and
   degraded-mode behavior in a staging-like environment.

## Anti-patterns

Reject unbounded-cardinality labels, alert-on-log-volume, health endpoints that
lie, dashboards without a decision, missing correlation IDs, sensitive logs,
and runbooks that have never been executed.

## Evidence

Record sample events, metric names, trace path, alert firing evidence, runbook
path, smoke output, and rollback result. State what cannot be observed.

## Next step

Hand implementation to `implementation`, test-first per
`.claude/skills/implementation/references/test-driven-development.md`; hand release evidence to
`reviewer` (mode: release-readiness) and this skill's releasing procedure;
record decisions with `documentation`.

## Routing

- Enter before production launch, after incidents, or when ownership and
  failure detection are unclear.
- Pair with `code-review` (performance lens) for saturation and capacity risks.
- Do not use to replace incident response or a provider-specific operations
  runbook.
- Vetted external references (Google SRE books, OpenTelemetry, awesome-sre):
  `.claude/rules/observability-resources.md` (path-scoped; pointer only).

## Success

Critical journeys have measurable objectives, actionable alerts, safe telemetry,
tested runbooks, and evidence that rollback and degraded behavior work.
