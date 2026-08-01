# Prerequisites checklist

A running checklist of external services/API keys needed across projects — one
place to look instead of digging through each project's own `HANDOFF.md`. Written
by hand whenever a task hits a must-supply credential it can't generate itself; not
preloaded at `SessionStart` — consulted on demand, same treatment as
`decisions/`/`ISSUES.md`.

The deployment skills that used to own this file were deleted on 2026-08-01. The
entries below are still accurate as credential records; the "Used by" lines that
name a skill are historical.

Format per entry:

```
## <Service name>
- **Used by**: <project slug(s) under ~/mvp-builds/, or "global tooling">
- **Env var**: `NAME`
- **Get it**: <one-line instruction/URL>
- **Configured**: yes | no
```

<!-- Entries below, newest service at the top. Update "Configured" in place once you've
set it up -- don't delete an entry just because one project stopped needing it, unless
no project uses it anymore. -->

## GitHub CLI (`gh`)
- **Used by**: global tooling — repo creation/push for every `mvp-builder` project
- **Env var**: n/a (session-based auth via `gh auth login`)
- **Get it**: installed 2026-07-25 (v2.96.0, user-local zip install at
  `%LOCALAPPDATA%\GitHubCLI`, added to user `PATH` — no admin rights needed,
  the MSI installer requires elevation and was abandoned for that reason).
  `gh auth login` still needs to be run once, by the user, in an interactive
  browser session — this is an OAuth/device-code flow tied to their GitHub
  account identity, which cannot be scripted or delegated (same category as
  MFA or payment approval). Once run, the token persists on this machine, so
  this is a one-time cost, not a per-project or per-session one.
- **Configured**: yes — authenticated 2026-07-25 as `NG-VikasV` (HTTPS,
  scopes: gist/read:org/repo/workflow). Confirmed working on this machine.

## Render API token
- **Used by**: `deployment-pilot` — turns a Render Blueprint deploy from a
  dashboard click-through into a scriptable `curl` call against Render's
  REST API. Without this, Blueprint creation needs a human in the Render
  dashboard every time (confirmed necessary during the `trending-news-hub`
  deploy 2026-07-25 — no Render CLI/API access was available, so the
  Blueprint had to be created manually).
- **Env var**: n/a (pass as a bearer token to Render's API directly)
- **Get it**: Render dashboard → Account Settings → API Keys → create one
- **Configured**: unconfirmed

## Vercel CLI
- **Used by**: global tooling — default first choice in `stack-selector`'s Tie-Break Order
- **Env var**: n/a (session-based auth via `vercel login`)
- **Get it**: run `vercel login` once
- **Configured**: unconfirmed
