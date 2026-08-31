# Error monitoring / observability — free tier

- **Use Sentry's free Developer plan as the default for error tracking** —
  already wired as an MCP server in this layer (`.mcp.json`'s `sentry`
  entry); it needs authorization before its tools are usable — via `claude
  mcp` or the MCP-management slash command in an interactive session —
  never fill in a Sentry token yourself on the user's behalf.
- **Free tier limits (verified against `sentry.io/pricing`, 2026-08):**
  - 5,000 error events per month, across all projects
  - 5,000,000 spans (tracing) per month
  - **1 user only** — the real ceiling for a small team, not the event
    count. A second teammate needs their own Sentry account or the team
    shares one login, which is a real operational tradeoff to decide
    explicitly, not discover later.
  - 30-day data retention
  - 10 custom dashboards, basic email alerts
- **A production app without error monitoring is not production-grade,
  free tier or not** — this is the one category in this rule set with no
  "skip it for the MVP" option. The free monthly quota is enough for a
  real small-user-base app; it is not enough to leave unhandled a bug
  that fires on every page load — fix the loop, don't just watch the
  quota burn.
- **Pair with `release-git/references/observability-sre.md`**, already
  part of this layer's own release procedure — Sentry supplies the error
  signal; that reference owns the rest of the readiness sequence (logs,
  metrics, alerts, dashboards) generically.
