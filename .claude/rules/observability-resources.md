---
paths:
  - "docs/plans/**/*.md"
  - "docs/specs/**/*.md"
  - ".claude/skills/release-git/references/observability-sre.md"
---

# Observability / SRE resources

When work defines what to monitor — SLIs/SLOs, alerts, tracing, dashboards,
incident response — consult the highly-rated external references below
before deciding from the request text alone. They are references to read,
not dependencies: nothing here is vendored into this repo or installed as a
skill. Vetting (stars, last commit, license) is recorded in
`docs/research/2026-09-03-tech-resources.md`.

| Resource | Repo | What it gives you |
|---|---|---|
| Google SRE books | `sre.google/books` (guide) | SLI/SLO/error-budget definitions, alerting philosophy, incident and postmortem practice |
| OpenTelemetry docs | `open-telemetry/opentelemetry.io` | The vendor-neutral instrumentation standard — traces, metrics, logs, semantic conventions |
| Awesome SRE | `dastergon/awesome-sre` | Curated index into SRE books, articles, tools, newsletters |
| Awesome Observability | `adriannovegil/awesome-observability` | Curated index for metrics / logs / traces / visualisation tooling |

- **This list is a floor, not a ceiling.** A couple of entries update
  slowly; re-check at the time of the work and prefer a fresher equivalent
  when one exists.
- **Ground, don't copy wholesale.** Use these to pick signals and
  thresholds; the in-repo readiness sequence stays in
  `.claude/skills/release-git/references/observability-sre.md`.

The metrics/dashboard tool pairing (Prometheus + Grafana, OpenTelemetry for
traces) is named in `engineering-standards`' backend reference, not here.
