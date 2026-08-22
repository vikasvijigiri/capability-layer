# Platform packs

`SKILL.md` carries the *shape* of a release and deliberately no vendor commands:
detect the target, say what cannot be undone, deploy, smoke, know the rollback.
That shape is identical on every platform. What differs is four strings, and they
live here so `SKILL.md` never grows an `if vercel: … elif render: …` branch that
every project pays for regardless of what it deploys to.

Read **one** section — the one matching the target you detected. Loading all of
them to deploy to one is the waste this file exists to prevent.

## How to detect the target

From the repo, never from memory:

| Present | Target |
|---|---|
| `vercel.json`, `.vercel/` | Vercel |
| `render.yaml` | Render |
| `fly.toml` | Fly.io |
| `Procfile`, `app.json` | Heroku |
| `k8s/`, `*.yaml` with `kind: Deployment` | Kubernetes |
| `Dockerfile` + a registry in CI | container registry |
| `.github/workflows/*deploy*` | whatever that workflow targets — **read it first** |
| none of the above | **there is no deploy target.** Say so and hand to `documentation` |

The last row is the common case and the one most often got wrong: inventing a
release for a library or a docs change is worse than skipping the stage.

---

## Vercel

    npx vercel --prod                    # deploy
    npx vercel ls                        # recent deployments, newest first
    npx vercel rollback <deployment-url> # promote a previous one

**Irreversible:** the production alias moves the moment the build succeeds. There
is no confirmation step, so the approval has to happen before the command.
**Smoke:** `python tools/smoke.py --url https://<prod-domain>/ --expect-status 200`
**Rollback:** `vercel rollback` to the previous URL from `vercel ls`. Record that
URL in `HANDOFF.md` *before* deploying — it is the only place it survives the
session.

## Render

    curl -fsS -X POST "https://api.render.com/v1/services/$SVC/deploys" \
         -H "Authorization: Bearer $RENDER_API_KEY"

**Irreversible:** a failed deploy can leave the service in a restart loop.
**Smoke:** the service URL, after `deploy.status == "live"` — Render reports
`created` immediately, which is not the same thing.
**Rollback:** redeploy the previous commit SHA. Capture it first.

## Fly.io

    fly deploy
    fly releases            # numbered, newest first
    fly releases rollback <n>

**Irreversible:** `fly deploy` runs release commands, and a release command that
performs a migration has already run by the time the health check fails.
**Smoke:** `fly status` plus a real request — `status` reports the machine, not
the app.

## Heroku

    git push heroku main
    heroku releases
    heroku rollback v<n>

**Irreversible:** release phase runs migrations before the new dynos take traffic.
**Rollback** reverts code, **never the database**.

## Kubernetes

    kubectl apply -f k8s/ && kubectl rollout status deploy/<name>
    kubectl rollout undo deploy/<name>

**Irreversible:** nothing, if `rollout status` is watched and the rollout is
undone on failure — which is the point of watching it.
**Smoke:** port-forward and probe, or hit the ingress.

---

## Migrations, on every platform

The one thing no rollback command undoes. `git revert` restores code; nothing
restores a dropped column.

- A migration is a **separate, separately-approved** step from the deploy.
- Additive first: add the column, ship code that writes both, backfill, *then*
  remove the old one. Three deploys, each individually reversible.
- `stop-finalization/06-artifact-autocommit.py` refuses to auto-commit anything matching
  `_hooklib.MIGRATION_PATH_PATTERNS`, so a migration cannot land unattended. That
  is a floor, not a review.
- Say out loud, before running one: what it drops, and what restores it. If the
  answer to the second is "a backup", name the backup.
