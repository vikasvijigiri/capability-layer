# Skill quality: releasing vs affaan-m/ECC deployment skills

Comparable: `affaan-m/ECC` (public GitHub repo), `skills/deployment-patterns/SKILL.md`
(closest match — deployment strategies, Docker, CI/CD, health checks, rollback
and production-readiness checklists); also read `skills/canary-watch/SKILL.md`
as a secondary comparable for the post-deploy smoke/observation half, and
`skills/delivery-gate/SKILL.md` to rule it out (it is a session-hygiene Stop
hook — learning-log staleness and disk space — not a release-readiness gate,
despite the name). All three read in full via `mcp__github__get_file_contents`.

Confirmed: `.claude/skills/releasing/references/PLATFORMS.md` still covers only
Vercel, Render, Fly.io, Heroku and Kubernetes — no AWS, GCP or Azure section,
and no generic container-registry runbook beyond a one-line detection-table
entry ("`Dockerfile` + a registry in CI → container registry", no commands).

## Gaps in ours (`.claude/skills/releasing/SKILL.md`, 281 lines)

1. **No deployment artifacts at all — only process.** ECC's
   `deployment-patterns` ships copy-pasteable Dockerfiles (Node, Go,
   Python/Django, each multi-stage, non-root, with `HEALTHCHECK`), a full
   GitHub Actions pipeline (test → build → push → deploy), Kubernetes
   liveness/readiness/startup probe YAML, and a Zod env-schema validation
   example. Ours (and `references/PLATFORMS.md`) never shows what a health
   endpoint or a CI pipeline should look like — it assumes both already exist
   and only covers detect-target → deploy → smoke → rollback. Fix: a
   `references/health-checks.md` with one worked health-endpoint example
   (the `/health` + `/health/detailed` pattern ECC shows) so "prove it is
   serving" has a concrete shape to point at, not just a curl command.

2. **No worked example of the deliverable.** ECC's `canary-watch` shows a
   full rendered output — a "Canary Report" markdown table with Status,
   baseline, delta per row. Ours describes what the irreversibility statement
   and smoke-check evidence must contain (SKILL.md lines 141–167) but never
   shows one filled in with real values. A new user has to infer the shape
   from prescription alone. Fix: add one worked example block to SKILL.md or
   `references/observability-sre.md`.

3. **`observability-sre.md` names dimensions but no concrete thresholds.**
   ECC's `canary-watch` gives numeric alert tiers out of the box (LCP > 4s
   critical, CLS > 0.1 warning, error-rate deltas). Ours says "Define SLI/SLO
   targets and error budgets with windows" (line 19) — correct methodology,
   but a team with no prior SLOs gets no starting numbers to anchor on.

## Where ours is stronger

1. **Tool-enforced shipment gate vs a prompt-only checklist.** Ours uses
   `AskUserQuestion` for the single explicit shipment approval, records the
   decision to a ledger (`tools/chain.py --gate 2 --decision ship|hold|reject
   --reason`), and `test_process_router.py` asserts the skill both calls the
   tool and states the rule (SKILL.md lines 13–61). ECC's entire release
   gate is a markdown `- [ ]` "Production Readiness Checklist" — nothing
   stops an agent from claiming every box checked with no verification, and
   there is no decision record at all. This is the same asymmetry the
   `writing-plans` vs ECC comparison found: tool-enforced beats prompt-only.

2. **A default-deny spend guard.** `pre-deploy/01-spend-guard.py` denies any
   Bash/PowerShell call invoking a cloud CLI outside known-free command
   shapes (SKILL.md lines 221–228). ECC has no equivalent — nothing in
   `deployment-patterns` or `canary-watch` prevents an agent from running an
   arbitrary paid cloud command during a "production readiness" pass.

3. **Migration handling is a strategy, not a checkbox.** Ours mandates the
   additive-first sequence — add column, ship code writing both, backfill,
   remove old, three separately-reversible deploys — plus a hook
   (`post-run/06-artifact-autocommit.py`) that refuses to auto-commit
   anything matching a migration path pattern (PLATFORMS.md lines 86–98).
   ECC's rollback checklist has one line, "Database migrations are
   backward-compatible (no destructive changes)," with no sequencing and no
   mechanical backstop.

4. **Roll-back-first ordering is a hard rule, not a checklist item.** Ours
   requires rollback, then a verified smoke-check of the rollback itself,
   then `systematic-debugging` — "roll-forward is a decision the user makes
   with the outage in front of them, never a default you pick" (SKILL.md
   lines 208–219). ECC's rollback checklist item ("Rollback tested in
   staging before production release") is a pre-deploy readiness check, not
   an incident-response ordering rule — it says nothing about what to do
   once something has already gone red in production.

## Verdict

Ours enforces the *approval and rollback discipline* of a release far more
rigorously than ECC does (tool-gated approval, ledger, spend guard, migration
sequencing, roll-back-first ordering); ECC is the stronger *reference* for
what to actually deploy (Dockerfiles, CI pipeline, health-endpoint code,
concrete alert thresholds) — the fix is to keep our gates and borrow one or
two worked artifacts so the skill's prescriptions have a shape to point at.
