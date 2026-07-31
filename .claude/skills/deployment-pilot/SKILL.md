---
name: deployment-pilot
model: haiku
description: Deploys to the free-cloud target matching stack-selector's choice, provisions secrets and a health endpoint, and verifies the live URL against the PRD's acceptance criteria. Owns the repo-visibility default and the generatable-vs-must-supply secrets split. Use for any deploy, host, publish or hosting-setup task, and for "put this online", "ship it", "get this online", "deploy it", "can people use it yet", "give me a link to share", "host this somewhere", "make it live". Prefer this over hand-rolling deploy steps - it enforces the zero-cost ceiling and never deploys without explicit approval. Do NOT use for local-only runs.
effort: low
argument-hint: "[target, or leave blank to infer from the ADR]"
user-invocable: true
allowed-tools:
  - Read
  - Edit
  - Bash(vercel:*)
  - Bash(netlify:*)
  - Bash(flyctl:*)
  - Bash(railway:*)
  - Bash(gh:*)
  - Bash(curl:*)
  - Grep
  - AskUserQuestion
  - Skill
provides: [deployment, health-endpoint, secrets-triage, prerequisites-checklist]
requires: [stack, implementation]
produces_artifact: true
retryable: true
---

# Deployment Pilot

Takes a reviewed, QA-passed build to a live URL on the host `stack-selector` chose.
Distinct action space from `code-review`/`git-delivery-guard` — this skill provisions
billable infrastructure, they review and gate code. Reusable standalone for any deploy
task, not just inside `mvp-builder`.

## Autonomy Defaults

- **Repo visibility: private, always** — unless the original goal explicitly said
  "public," "open-source," or "portfolio." Free-tier hosts deploy private repos with no
  cost delta, so this default has zero tension with the zero-cost ceiling; never infer
  "public" from anything short of an explicit statement.
- **Secrets: generate what's generatable, escalate what isn't.** Random session/JWT/
  signing keys are generated inline. A real third-party API key (Stripe, OpenAI, etc.)
  that the goal implies but nobody supplied is a blocker for `error-recovery`'s
  escalation path — that feature/integration is skipped and logged, never invented or
  stubbed with a fake key. Also add/update an entry in `.claude/PREREQUISITES.md`
  (global, not per-repo) for that service — the durable, cross-project checklist, not
  just this one project's `HANDOFF.md` blocker. If an entry for that service already
  exists, add this project to its "Used by" line rather than duplicating the entry.
- **Health endpoint by default.** Provision a `/health` route (or equivalent) even for a
  simple build — it's what this skill's own live-verify step hits, not just the root
  page, and it's the cheapest form of observability a free-tier MVP can have. Wire
  structured logging by default; add Sentry only when stack/complexity actually
  warrants it.
- **Rollback**: app-code rollback is inherent to the chosen hosts (Vercel/Netlify/
  Railway/Render all fail a bad build before replacing the previously-live version) —
  don't build anything for that. **Data/schema rollback is not automatic** — any
  feature that changes a schema must ship migration + verify + rollback/down-migration
  (or an explicit one-line note why none is possible) as one unit, never forward-only.

## Steps

1. **Confirm CLI auth.** An unauthenticated CLI is a blocker (the user's one-time setup,
   not something to resolve interactively) — check before attempting a deploy command.
2. **Provision secrets** per the split above.
3. **Deploy** via the host's CLI. Every deploy command runs through `deploy_spend_guard.py`
   mechanically — if it's denied, that's a blocker, not something to retry with a
   different flag combination hoping it slips through.
4. **Verify the live URL against the PRD's acceptance criteria** — this is the acceptance
   gate, not a generic "does the page load" smoke check: every criterion
   `requirements-analyst` wrote maps to one concrete pass/fail check against the
   deployed product, plus the `/health` endpoint responding.
5. **Report**: live URL, what's confirmed working against which acceptance criteria, and
   anything that had to be skipped (missing secret, denied deploy command) as a blocker.

## Render-specific notes

Found live during an actual deploy, not theoretical — apply these whenever `stack-selector`
picked Render:

- **Migrations must run on every deploy.** `render.yaml`'s `buildCommand` needs the
  project's migration command chained on (`npm install && npm run migrate`, or
  equivalent) — otherwise the app 500s on its very first request to any DB-touching
  route, because the schema was never applied to the freshly-provisioned Postgres
  instance. Idempotent migration runners make this safe to run on every deploy, not
  just the first.
- **Use `runtime: <lang>`, not `env: <lang>`.** Render renamed this Blueprint key;
  `env` still works via back-compat but is deprecated — don't write it into a new
  `render.yaml`.
- **A Render API token turns this from a dashboard click-through into a scriptable
  step.** Without one, Blueprint creation needs a human in the Render dashboard
  (account-ownership action, same category as `gh auth login` — don't try to script
  around it). With one, `curl` (already an allowed tool here) against Render's REST
  API can create the Blueprint/services directly. Add an entry to
  `.claude/PREREQUISITES.md` for it, same pattern as the `gh` CLI entry, so this
  only needs setting up once per machine rather than once per project.
- **Read exactly how a secret gets used before setting its value** — don't infer its
  shape from the variable name alone. A GitHub Actions secret named `INGEST_URL` set
  to a full endpoint URL (`.../api/ingest`) silently produced a double path and a 404,
  because the workflow file itself appended `/api/ingest` to it. Grep the actual
  consuming script/workflow first.

## Relationship to other skills

- Consumes `stack-selector`'s chosen host and `code-review`'s pre-deploy gate pass —
  never deploys something that hasn't cleared review.
- Hands blockers to `error-recovery`'s escalation path, landing in `HANDOFF.md`'s
  `### Autonomous Run Blockers` section — never invents a workaround for a missing
  credential or a denied command.

## Note on project-local overrides

A repo can have its own `.claude/skills/deployment-pilot/` with a repo-tailored version
(e.g. a project that's already provisioned on a specific paid/enterprise host and needs
deploys targeted there instead of the free-tier default). Where both exist, the
project-local one takes precedence for that repo — this global version is the default
otherwise.

## Human gate

**Never deploy without passing the gate first**, even when the target is a free tier and the change looks small -- a live URL is outward-facing the moment it exists, and cost ceilings are not the only thing at stake.

Gate each of these separately, because each fails differently: provisioning infrastructure, writing secrets to the provider, and promoting to a public URL. State repo visibility in the brief -- a public repo is not undoable in the way people assume once it has been indexed.

Invoke `approval-brief` and let it run the `AskUserQuestion` dialogue. Do not write your own prose "shall I proceed?" -- the dialogue shape, the option wording and the no-bundling rule live in that one skill so they cannot drift apart here.
