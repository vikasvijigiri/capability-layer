---
name: business-outcome-review
model: opus
description: Checks whether a shipped build actually addresses the original business goal, not just whether its acceptance criteria technically passed. Cross-references the goal statement against the PRD's criteria for fidelity, and against real usage signals once they exist. Use whenever a build claims to be finished or done, after deployment, and when asked "did this solve the problem", "does this meet the goal", "are we actually done", "did this actually help", "was it worth building", "are people using it", "did it move the needle". Prefer this over declaring completion yourself - passing tests and solving the business problem are different claims. Do NOT use mid-build.
effort: high
argument-hint: "[the original goal to check against]"
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
provides: [outcome-review]
requires: [goal, acceptance-criteria]
produces_artifact: false
retryable: true
---

# Business Outcome Review

Distinct question from everything else in this system: `code-review`/`QA` ask "does
this pass its acceptance criteria." This skill asks "do those acceptance criteria,
now that they're met, actually mean the original business problem is solved." A
project can pass every test `requirements-analyst` wrote and still miss the point, if
scope-cutting or interpretation quietly drifted from the real goal along the way.

Report-only — same discipline as `no-slop-check`/`context-economy-audit`. Findings
feed `HANDOFF.md`'s `Open Questions` (via `knowledge-manager`), not an automatic fix.

## Two modes — be honest about which one applies

**Mode 1: No usage data yet** (a same-day or otherwise fresh deploy). The only
honest check available is **requirements fidelity**, not outcome measurement — don't
pretend to assess real-world impact that hasn't had time to happen yet. Compare the
original goal/objectives statement (`TASK.md`'s `Goal` field, or the request that
started the work) against the PRD's acceptance criteria line by line:
- Does each criterion still trace back to the stated business goal, or did it
  quietly become "ship something that resembles the goal"?
- Did anything in the v1 cut list remove something the *business* goal actually
  needed, versus something genuinely out of scope for an MVP?
- Is there a criterion that's trivially satisfiable without addressing the real
  problem (e.g., "an endpoint returns JSON" instead of "a user can actually find
  what they came for")?

**Mode 2: Usage data exists** (analytics, logs, health-check history, real traffic
over time). Now check actual outcomes, not just fidelity:
- Is the thing being used at all — any real traffic/requests beyond your own testing?
- Which shipped features show zero real usage — candidates to cut in a v2, not
  evidence the build failed.
- Error rates / uptime history against the free-tier host's own limits.
- Whichever metric the original goal implied as success (grep the goal statement for
  anything measurable — "reduce time to X," "let users do Y" — don't invent a metric
  that was never stated).

Never blend the two modes in one report — say explicitly which mode this run is in,
so "no usage data yet" doesn't get misread as "nothing to evaluate."

## Steps

1. Find the original goal statement (repo's `TASK.md` `Goal` field for the top-level
   build task, or the PRD in `decisions/`/`HANDOFF.md` if that's where it lives) and
   the acceptance criteria that were derived from it.
2. Determine which mode applies — check for actual usage signals (real ingest/request
   logs, analytics, uptime history) before assuming Mode 1.
3. Run the applicable checks above. Cite the specific goal line and the specific
   criterion/metric for every finding — a vague "seems fine" or "seems off" isn't a
   finding.
4. Report: which mode, what was checked, concrete findings (goal line vs.
   criterion/metric, not general impressions), and anything that's a genuine open
   question rather than a clear miss.
5. Don't fix anything. A real finding here (drifted scope, a criterion that missed
   the point) is a `decisions/` entry or a new `TASK.md` follow-up task, made
   through `knowledge-manager` — not a silent edit.

## Relationship to other skills

- Consumes `requirements-analyst`'s PRD and `knowledge-manager`'s `TASK.md`/
  `HANDOFF.md` — never redefines what the goal was, only checks fidelity to it.
- Distinct from `deployment-pilot`'s live-URL acceptance-criteria check — that
  confirms criteria pass; this asks whether passing criteria was ever the same thing
  as solving the problem.
- A finding that scope genuinely drifted from the original goal is a trigger for a
  new `decisions/` entry (via `knowledge-manager`), not a reason to silently expand
  scope on the spot.
