# Releasing procedure

Merged from the former `releasing` skill. Get delivered work running in a
real environment, with signals. Workflow stage 8.

At the shipment gate, present the release candidate, smoke evidence, rollback,
<!-- GATE 2: shipment approval. The chain has two; see .claude/workflow.md. -->
and target, then use `AskUserQuestion` for the single explicit shipment
approval. Do not ask for approval earlier in the workflow.

**Bring the release candidate report.** It is what this gate reviews:

    python tools/release_candidate.py --plan <plan>

Wheel version and hash, the target repository's own tier, the SBOM, the licence
verdict, the risk tier, the changed-path count, and **the rollback result** —
which comes from an uninstall that actually ran in a scratch repo, not from a
paragraph promising one. Exit `0` ready · `1` a check failed · `2` a fact could
not be determined, and **2 is not 0**: a candidate with an unestablished fact is
not one anybody can approve.

Slow by design — it builds a wheel and a virtualenv. Run it before opening the
gate, not during.

**Show the risk tier in the question**, from
`python tools/scope.py --plan <plan>` — `0` low, `1` medium, `2` high, with the
clause that forced it. A reader deciding whether to ship needs to know that this
change touches a migration or the installer, and that fact is computed rather
than remembered.

**Record the decision**, whichever way it went:

    python tools/chain.py --gate 2 --decision ship|hold|reject --reason "<their words>"

Same ledger, same shape as Gate 1, reason verbatim. A shipment decision that
exists only in a transcript is not a record anybody can audit afterwards.

**The tier never waives this gate.** A low-risk shipment still asks. Nothing in
this layer may push, merge, publish or deploy on an inferred yes, and a tier
computed by the system that wants to ship is not the thing that gets to waive
the one rule with no exceptions. The tier decides what the question **shows**,
never whether it is **asked**.

Offer ship, hold, and reject as real options, and **say in the question that
hold and reject take the reason as free text** — the tool appends its own
"Other" for that; never add one. Record the answer verbatim, including anything
in its notes.

**A prose question does not count**, however plainly it is worded. The
approval has to be a click. `test_process_router.py` asserts this skill both
calls the tool and states this rule.

A rejected candidate is not a failed check and gets no repair budget. Record why
it was held, and route by what the reason actually says: a defect goes to
`debugging`, a missing signal to the observability reference below, a
changed mind to `documentation` so the decision not to ship is durable
rather than a thing someone remembers. Never re-present an unchanged
candidate — `tools/loop.py` refuses it.

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
`documentation`. Inventing a release for work that has none is worse than
skipping the stage.

## Three preconditions, checked in order

Do not deploy until all three hold. Each is a question with a command behind it.

1. **The work was delivered, and you can name what goes live.** The
   delivering procedure ran, and the exact commit or artifact the target
   builds from exists. Name it — `git rev-parse --short HEAD`, a tag, a
   build ID. "The latest code" is not a version.
2. **The rollback exists and you have named it before deploying.** One command,
   or a written procedure with the previous good version in it. If you cannot
   name the previous good version, you do not have a rollback — say so and stop.
3. **The checks pass on the tree being released.** Run `/verify` and quote it. A
   run from before the merge proves the pre-merge tree, not this one.

State which three you actually ran. "All good" is not one of them.

## Detecting the target — never guess it

Resolve in this order and stop at the first hit:

1. **What the user said.** A named target always wins.
2. **Repo evidence**, one file at a time: `vercel.json`, `render.yaml`,
   `fly.toml`, `netlify.toml`, `railway.json`, `app.yaml`, `serverless.yml`,
   `Procfile`, a `deploy` job in `.github/workflows/`, a `deploy` target in a
   `Makefile` or `justfile`, k8s manifests, a `publish` script in the package
   manifest.
3. **Ask.** Zero matches or two, ask. Do not pick the more likely one.

Report the detection as a file path, not an impression.

**Environments are a parameter, not a ladder you invent.** If the repo names
more than one target, deploy the lowest first, smoke it, and only then offer the
next — each with its own approval.

**Platform specifics live in `references/PLATFORMS.md`, never in this file.**

## Before the deploy — the irreversibility statement

One line each, out loud, then wait for a yes:

- **What** goes live — the version from precondition 1.
- **Where** — the target from detection, named exactly.
- **Who sees it** the moment it lands.
- **The rollback command**, from precondition 2.
- **What rollback does not undo** — applied migrations, sent mail, fired
  webhooks, purged caches, anything a third party already consumed.

## The smoke check is the deliverable, not the deploy

**A deploy tool exiting 0 means the upload succeeded.** It does not mean the
change is serving.

Prove it: request the health endpoint, or the surface that actually changed, and
**quote the real response**. An unquoted smoke check did not happen.

```bash
python tools/smoke.py --url https://<target>/ --expect-status 200 --expect-text '<something real>'
```

## After the smoke check — observe and close the release

1. Confirm the target's logs, health metrics, error rate, latency, and key
   business signal for the agreed observation window.
2. Compare the observed signal with the pre-release baseline.
3. If the signal breaches the agreed threshold, roll back using the named
   procedure, smoke-check the rollback, and then enter `debugging`.
4. If the signal is healthy, hand the evidence to `documentation`, including
   residual risk, follow-up monitoring, and who owns the next action.

## Platform commands live in a pack, not here

Read **one** section of [`references/PLATFORMS.md`](PLATFORMS.md) — the one
matching the target you detected.

## When it goes red — roll back first, diagnose second

1. Run the rollback named in precondition 2.
2. Smoke the rolled-back environment and quote it.
3. **Then** `debugging`, on the failure, with the environment stable.

## The gate you will meet

| Gate | Fires when | The actual fix |
|---|---|---|
| `permission-security/00-dispatch.py` (spend-guard check) | A Bash/PowerShell call invokes a cloud CLI outside its known-free command shapes | Use the free-tier-shaped command it names, or get explicit approval for spend |

## Red Flags — stop, do not release

| Said | Why it bites |
|---|---|
| "The deploy CLI exited 0, so it's live." | The upload succeeded; the app may be crash-looping |
| "I'll find the rollback if we end up needing it." | Name it before the deploy |
| "It's probably Vercel, there's a `next.config.js`." | Framework ≠ host |
| "They approved the merge, so the deploy is approved." | Two blast radii, two decisions |
| "It's only a config change, it doesn't need a smoke test." | Config is what most outages are |
| "Roll forward — rolling back loses the fix." | Roll back, then diagnose |
| Branching on the platform inside this file | Platform packs live in `references/` |

After the smoke check and observation window, dispatch `reviewer` (mode:
release-readiness) for an independent readiness check when the harness
supports subagents. Missing health evidence is BLOCKED, not a successful
release.

## Operating what you released

Read [`references/observability-sre.md`](observability-sre.md) before the
first release to a target, and after any incident — SLOs, alerts,
dashboards, health checks, runbooks, capacity signals, rollback evidence.

## Next step

**The terminal state is invoking `documentation`.** `LOG.md` records what
version went live, where, and when; `HANDOFF.md` carries the rollback command
forward.
