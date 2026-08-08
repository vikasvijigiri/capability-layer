---
name: releasing
description: Get delivered work running in a real environment, with signals. Triggers include "deploy this", "push it live", "release to staging", "is it live", "roll it back", "add SLOs", "set up alerts", "is this observable". Do NOT use to merge or open a PR (delivering), to prove it meets the brief (verifying-work), or to debug a failed deploy - roll back first. Use this whenever a change must reach a running target.
when_to_use: when work must reach a running environment
effort: low
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash Task
---

# Releasing

At the shipment gate, present the release candidate, smoke evidence, rollback,
<!-- GATE 2: shipment approval. The chain has two; see .claude/workflow.md. -->
and target, then use `AskUserQuestion` for the single explicit shipment
approval. Do not ask for approval earlier in the workflow.

Offer ship, hold, and reject as real options, and **say in the question that
hold and reject take the reason as free text** — the tool appends its own
"Other" for that; never add one. Record the answer verbatim, including anything
in its notes.

A rejected candidate is not a failed check and gets no repair budget. Record why
it was held, and route by what the reason actually says: a defect goes to
`systematic-debugging`, a missing signal to this skill's observability
reference, a changed mind to `knowledge-manager` so the decision not to ship is
durable rather than a thing someone remembers. Never re-present an unchanged
candidate — `tools/loop.py` refuses it.

Put delivered work into a running environment, prove it is actually serving, and
keep a way back. Workflow stage 9.

Cap visible output at ~500 tokens.

<HARD-GATE>
NEVER deploy, publish, promote or roll out without explicit approval in this
conversation.

This is CLAUDE.md's standing rule. Approval to merge is not approval to deploy —
they are different acts with different blast radii, and a yes to one says
nothing about the other. A merged branch changes a repository; a release changes
what users are looking at right now.

Approval is per target. A yes for staging is not a yes for production.
</HARD-GATE>

## Not every change needs this stage

Skip it when there is no environment: a library with no deploy target, a docs
change, a `.claude/` edit, a refactor that ships on the next release train. Say
"nothing to release — this repo has no deploy target" and go to
`knowledge-manager`. Inventing a release for work that has none is worse than
skipping the stage.

## Three preconditions, checked in order

Do not deploy until all three hold. Each is a question with a command behind it.

1. **The work was delivered, and you can name what goes live.** `delivering`
   ran, and the exact commit or artifact the target builds from exists. Name it
   — `git rev-parse --short HEAD`, a tag, a build ID. "The latest code" is not a
   version. A preview deploy of an unmerged branch is legitimate; say which
   branch.
2. **The rollback exists and you have named it before deploying.** One command,
   or a written procedure with the previous good version in it. Naming it
   afterwards is how a rollback turns out not to exist. If you cannot name the
   previous good version, you do not have a rollback — say so and stop.
3. **The checks pass on the tree being released.** Run `/verify` and quote it. A
   run from before the merge proves the pre-merge tree, not this one.

State which three you actually ran. "All good" is not one of them.

## Detecting the target — never guess it

Deploying to the wrong target is the expensive mistake in this stage, and it is
always caused by inference. Resolve in this order and stop at the first hit:

1. **What the user said.** A named target always wins.
2. **Repo evidence**, one file at a time: `vercel.json`, `render.yaml`,
   `fly.toml`, `netlify.toml`, `railway.json`, `app.yaml`, `serverless.yml`,
   `Procfile`, a `deploy` job in `.github/workflows/`, a `deploy` target in a
   `Makefile` or `justfile`, k8s manifests, a `publish` script in the package
   manifest.
3. **Ask.** Zero matches or two, ask. Do not pick the more likely one.

Report the detection as a file path, not an impression. `vercel.json:1` is
detection; "this looks like a Vercel project" is a guess wearing a fact's
clothes.

**Environments are a parameter, not a ladder you invent.** If the repo names
more than one target, deploy the lowest first, smoke it, and only then offer the
next — each with its own approval. If it names one, there is one. Do not
manufacture a staging step the project does not have, and do not skip one it
does.

**Platform specifics live in `references/<platform>.md`, never in this file.**
This skill knows the shape — detect, state, deploy, smoke, roll back — and never
the vendor. If a platform's commands are worth writing down, write them there
and read them at step 2. Adding a platform must not add a branch here.

## Before the deploy — the irreversibility statement

One line each, out loud, then wait for a yes:

- **What** goes live — the version from precondition 1.
- **Where** — the target from detection, named exactly.
- **Who sees it** the moment it lands.
- **The rollback command**, from precondition 2.
- **What rollback does not undo** — applied migrations, sent mail, fired
  webhooks, purged caches, anything a third party already consumed.

That last line is the one people skip, and it is the one that matters. A
reversible deploy sitting on top of an irreversible migration is not reversible.

## The smoke check is the deliverable, not the deploy

**A deploy tool exiting 0 means the upload succeeded.** It does not mean the
change is serving. These are different claims and only the second one is the
point of this stage.

Prove it: request the health endpoint, or the surface that actually changed, and
**quote the real response**. Include the version if the response carries one.
An unquoted smoke check did not happen — this is `verifying-work`'s rule and it
binds harder here, because the thing you are asserting about is live.

If the target has no way to prove the change is serving, that is a finding worth
recording, not a reason to skip the check.

## After the smoke check — observe and close the release

The smoke check proves initial serving, not operational health. Before declaring
the release complete:

1. Confirm the target's logs, health metrics, error rate, latency, and key
   business signal for the agreed observation window. Use the target's existing
   dashboards or checks; do not invent a healthy value.
2. Compare the observed signal with the pre-release baseline. Record the
   version, target, observation window, and exact evidence.
3. If the signal breaches the agreed threshold, roll back using the named
   procedure, smoke-check the rollback, and then enter `systematic-debugging`.
4. If the signal is healthy, hand the evidence to `knowledge-manager`, including
   residual risk, follow-up monitoring, and who owns the next action.

No release is closed by a deploy exit code or a single HTTP response alone.

**The mechanism.** This skill mandated a smoke check long before anything could
perform one:

```bash
python tools/smoke.py --url https://<target>/ --expect-status 200 --expect-text '<something real>'
```

It optionally starts the app (`--start "npm run dev"`), waits for it to answer,
probes, and tears the whole process tree down afterwards. `--expect-text` is what
makes it a check rather than a ping: a 200 from an error page is still a 200.

## Platform commands live in a pack, not here

Read **one** section of [`references/PLATFORMS.md`](references/PLATFORMS.md) — the
one matching the target you detected. It carries deploy, smoke and rollback for
Vercel, Render, Fly, Heroku and Kubernetes, the detection table that decides which
applies, and the migration rules that hold on all of them.

Loading all of them to deploy to one is the waste that file exists to prevent,
and an `if vercel: … elif render: …` branch in this file is the failure mode the
pack exists to avoid.

## When it goes red — roll back first, diagnose second

In this order, no exceptions:

1. Run the rollback named in precondition 2.
2. Smoke the rolled-back environment and quote it. A rollback you did not verify
   is a second unverified deploy.
3. **Then** `systematic-debugging`, on the failure, with the environment stable.

Debugging a live-broken environment while it is broken is the mistake this
ordering exists to prevent. Roll-forward is a decision the user makes with the
outage in front of them, never a default you pick because it feels quicker.

## The gate you will meet

| Gate | Fires when | The actual fix |
|---|---|---|
| `pre-deploy/01-spend-guard.py` | A Bash/PowerShell call invokes a cloud CLI (`vercel`, `netlify`, `flyctl`, `railway`, `supabase`, `doctl`, `heroku`, `aws`, `gcloud`, `az`) outside its known-free command shapes | Use the free-tier-shaped command it names, or get explicit approval for spend. It denies rather than asks, by design — it is built for runs with nobody present |

Allowlist-first: unrecognised is denied, not allowed. A denial is the hook
working. Never route around it by switching tool or shell.

## Red Flags — stop, do not release

- "The deploy CLI exited 0, so it's live."
- "I'll find the rollback if we end up needing it."
- "They approved the merge, so the deploy is approved."
- "Staging and prod are basically the same."
- "It's only a config change, it doesn't need a smoke test."
- "The migration is fine, it's backward compatible." Proven how?
- "Roll forward — rolling back loses the fix."
- "The spend guard is noisy, I'll run it through the other shell."
- "It's probably Vercel, there's a `next.config.js`."

**Each of these means: stop and ask, in this conversation.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Treating the deploy tool's exit code as the smoke check | The upload succeeded; the app may be crash-looping |
| Naming the rollback after the deploy | You find out it doesn't exist at the worst moment |
| Inferring the target from a framework file | Framework ≠ host; the wrong environment gets the change |
| One approval covering staging and production | Two blast radii, two decisions |
| Debugging the live failure before rolling back | Every minute of diagnosis is a minute of outage |
| Skipping the "what rollback does not undo" line | The reversible deploy sat on an irreversible migration |
| Branching on the platform inside this file | The next platform adds another branch, forever |

After the smoke check and observation window, dispatch `release-verifier` for
an independent readiness check when the harness supports subagents. Missing
health evidence is BLOCKED, not a successful release.

## Operating what you released

The observability-sre skill was separate; it is now
`references/observability-sre.md`. Read it before the first release to a target,
and after any incident - SLOs, alerts, dashboards, health checks, runbooks,
capacity signals, rollback evidence.

A deploy exit code is not health. The release is observed against a metric window
or it is not observed at all.

## Next step — you MUST take it

**The terminal state is invoking `knowledge-manager`.** `LOG.md` records what
version went live, where, and when; `HANDOFF.md` carries the rollback command
forward. A live environment nobody wrote down is one the next session cannot
roll back. A rollback that actually fired also earns an `ISSUES.md` entry.

## Routing

- Mandatory validator: the smoke check above. Nothing else proves this stage.
- Preceded by `delivering` — work reaches a branch before it reaches an
  environment. Entered from it only when a deploy target exists.
- Failure handoff: `systematic-debugging`, **after** the rollback, never before.
- Terminal handoff: `knowledge-manager`.
- Never invoked to fix what the smoke check found. That is a new unit of work
  and it re-enters the chain at its own stage.

## Success

The change is serving at a target the user named, a quoted smoke check proves
it, the rollback was named before the deploy rather than after, every gate that
fired was answered rather than bypassed, and `LOG.md` says what went live where.
