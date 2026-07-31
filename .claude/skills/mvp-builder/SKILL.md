---
name: mvp-builder
model: opus
description: Fully autonomous, zero-checkpoint MVP build — takes a goal/constraints statement once and runs PRD, architecture, design, scaffold, implementation, QA, deployment, handoff and outcome review unattended, on free tiers only, to a live product. Use for "build me an MVP", "build me a SaaS/app/platform", "build and deploy this", "build project from scratch", "create app unattended", or any ask for a complete product unattended. Prefer this over an interactive build when nobody is available to answer checkpoints - it logs blockers instead of stopping. Do NOT use for smaller asks or feature tweaks — use workflow-orchestrator instead.
effort: high
argument-hint: "[goal and constraints, stated once]"
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Skill
  - Agent
  - AskUserQuestion
  - TodoWrite
provides: [autonomous-build]
requires: [goal]
produces_artifact: true
retryable: false
---

# MVP Builder

Autonomous, zero-checkpoint MVP build: one approval up front, then a live product.

**This is a skill, not a workflow, and it has to be.** Claude Code has no workflow
runtime — `.claude/workflows/` holds documents, not executables, and nothing discovers
or fires them. A skill is the only thing invocable. The phase order below is
authoritative; [`build-mvp.js`](../../workflows/build-mvp.js) is the companion
*operational* spec (recovery loop, retry budget, model routing, JSON schemas) and is
read, never run — Node rejects it with `SyntaxError: Illegal return statement`.

## Read before starting

Governance, in this order, before phase 1:

- `CLAUDE.md` — mandatory rules, including the never-bypass-validators rule
- `.claude/skills/engineering-policy/SKILL.md` — standards and Definition of Done
- `.claude/routing/capabilities.md` — how to route each feature's work
- `.claude/blueprints/*.md` — CLAUDE.md requires preferring an existing blueprint
- `.claude/workflows/build-mvp.js` — recovery rules and per-phase prompts

Three companion files gate real behaviour and are easy to miss. Read each with its
skill, not from memory:

- `no-slop-check/checklist.md` — the skill explicitly refuses to be recalled
- `knowledge-manager/formats.md` — the formats for every doc this build writes
- `design-system/DESIGN.template.md` — the fork source for a new `DESIGN.md`

Then read each phase's own `SKILL.md` at the point of use.

## Phases

Run these in order. Each names the skill or agent that drives it — both are reachable,
which was not true before 2026-07-31, when `allowed-tools` was `[Read, Agent]` and every
skill in this table was unreachable.

| # | Phase | Drive with | Skip when |
|---|---|---|---|
| 1 | Intake & approval | `task-intake` | never |
| 2 | PRD | `requirements-analyst`, or `product-manager` agent | never |
| 3 | Architecture | `stack-selector`, or `solution-architect` agent | never |
| 4 | Scaffold | `repo-onboarding` | never |
| 5 | **Design** | `design-system` → `DESIGN.md`, then `frontend-ux-flow` → screens | no UI |
| 6 | Implement (per feature) | `backend-engineer` / `frontend-engineer` / `ai-engineer` agents | never |
| 7 | Review gate | `code-review`, then `no-slop-check` | never |
| 8 | QA | `qa-engineer` agent | never |
| 9 | Pre-deploy gate | `acceptance-verifier` against the PRD's criteria | never |
| 10 | Deploy | `deployment-pilot`, or `devops-engineer` agent | `trivial` builds |
| 11 | Handoff | `knowledge-manager` | never |
| 12 | **Outcome** | `business-outcome-review` | never |

Phase 5 is not optional decoration. `frontend-engineer` builds against `DESIGN.md` by
contract and `frontend-component-generator` refuses to run without one, so a UI build
that skips it either stalls or invents its own colour and spacing.

Phase 12 answers the only question that matters — whether the thing built addresses the
goal, not whether its tests pass. A run that ends at phase 11 can have built the wrong
product correctly.

## Recovery

A phase that fails twice goes to `error-recovery`; never retry ad hoc. An unrecoverable
phase is logged as a blocker in `HANDOFF.md` and the run continues around it where the
dependency graph allows — Scaffold and Architecture are foundational and abort instead.

Stop immediately on an infrastructure failure — session limit, rate limit, quota, provider
outage. These are not code bugs and no diagnose/fix cycle will pass them; one real run
burned 31 recovery calls against the same wall. `build-mvp.js` carries the detection
pattern.

## Workspace

Build inside this repo, at `builds/<project-slug>/`, with the slug derived from 2–4 key
terms in the goal and sanitised — an unsanitised brief field leaked into a directory name
once already.

Do **not** build to `~/mvp-builds/`, which is what this skill said until 2026-07-31.
Outside the repo none of the 22 hooks, 11 validators or the branch guard apply, so an
unattended run loses exactly the safety layer it most needs.

## Autonomy Principles

- **Zero Checkpoints**: overrides intermediate approval prompts during execution.
  Resolves ambiguities using skill defaults (`requirements-analyst`, `stack-selector`,
  `deployment-pilot`) or logs them as blockers in `HANDOFF.md`.
- **Deliberately exempt from the `approval-brief` gate.** Every other skill that deploys,
  provisions, migrates or pushes must open an approval dialogue first; this one must not,
  and that is the point of invoking it. Phase 1's approval is the *single* gate covering
  the whole run, so its dialogue must state plainly that it authorises deployment to a
  live public URL and secret provisioning without asking again. Do not add per-action
  gates here — they would break the one property this skill exists to provide. If a run
  needs gates, `workflow-orchestrator` is the correct skill.
- **Zero Cost Floor**: free-tier infrastructure, free APIs, open-weight models only. The
  *choice* of model and provider belongs to `stack-selector` and is recorded in its ADR —
  this skill sets the cost ceiling, it does not name products. A hardcoded model here
  went stale once and contradicted the skill that owns the decision.
- **Not retryable.** `retryable: false` is deliberate: re-running from phase 1 clobbers a
  partial build. Resume by invoking the failed phase's skill directly against the existing
  workspace.
- **Safety Limits Apply**: non-negotiable — no malicious content, no credentials
  committed.

## Final report

Live URL, repo path, feature list against the PRD, zero-cost confirmation, every logged
blocker, and the phase-12 verdict on whether the goal was actually met. State blockers
plainly; a report that omits them is a failed run described as a successful one.
