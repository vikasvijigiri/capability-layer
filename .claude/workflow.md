# Workflow

The chain of skills that takes any problem — a feature, a bug, a research
question, a decision — from a rough ask to a delivered result.

Each stage names the skill that owns it. Read the skill, not this file, for how
a stage works; this file exists to say **which** skill and **what it hands on**.

This file is copied into every repo the layer installs into, so it carries no
dates, no history and nothing specific to the repo it was written in. Why a
stage changed belongs in `LOG.md` and git.

---

## The chain

Ten stages on the line, two entered from anywhere. One skill each — a stage
with no owner is not a stage, and a skill owning two stages means the boundary
between them never actually occurs.

| # | Stage | Owner | Consumes | Produces |
|---|---|---|---|---|
| 1 | Frame | `task-brief` | a rough request | `TASK.md` — Goal / Constraints / Inputs / Outputs / Done-check / Out-of-scope |
| 2 | Design | `brainstormer` | an open question or a chosen direction | `docs/specs/YYYY-MM-DD-<topic>-design.md` |
| 3 | Plan | `writing-plans` | an approved spec | `docs/plans/YYYY-MM-DD-<feature>.md` |
| — | **Human approval** | — | the plan | a yes, in the conversation |
| 4 | Execute | `executing-plans` | an approved plan | the thing itself; ticked checkboxes |
| 5 | Validate | `verifying-work` | the result + the Done-check | a coverage verdict and the unbacked set |
| 6 | Sweep | `no-slop` | the verified tree | slop findings, then approved repairs |
| 7 | Review | `code-review` | the pending change | findings, then a sign-off receipt |
| — | **Human approval** | — | the findings | a yes, in the conversation |
| 8 | Deliver | `delivering` | verified, reviewed work | merged / pushed / PR opened, or kept |
| — | **Human approval** | — | the target and the rollback | a yes, per target, in the conversation |
| 9 | Release | `releasing` | delivered work + a deploy target | the change serving at a named target, a quoted smoke check, a named rollback |
| 10 | Record | `knowledge-manager` | what happened | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `MEMORY.md`, `decisions/` |

Stage 9 is the only stage that is **skipped by absence rather than by judgement**:
a repo with no deploy target has nothing to release, and `releasing` says so and
hands straight to 10. Stages 8 and 9 are two acts, not one — merging changes a
repository, releasing changes what users are looking at right now, and an
approval for one is not an approval for the other.

Three stages are not positions on the line. They are entered from wherever the
need arises and return to the stage that called them:

| Stage | Owner | Entered when | Returns to |
|---|---|---|---|
| Research | `research` | any stage needs evidence from outside your own knowledge | whatever asked |
| Diagnose | `systematic-debugging` | anything fails or behaves unexplainably, at any stage | the stage that hit the failure |
| Author | `skill-authoring` | this layer itself needs a new skill, or needs to decide it should not have one | whatever asked |

`skill-authoring` is off the line on purpose. Authoring a capability is not a
stage of delivering a product, and a numbered thirteenth stage describing how to
add stages is the kind of self-reference that makes the chain unreadable. It is
also the only stage whose refusal is a success: most requests for a new skill are
better served by a `references/` pack file, a command, or a hook.

### Two rules that keep the stage list from growing

**A stage exists only if some skill can be told "do that and stop".** Two stages
one skill performs in a single pass are one stage. A stage whose owner is
forbidden from performing it — review that also fixes, say — has no owner and is
not a stage.

**The order is plan → build → validate → review → deliver → record**, which is
where the established agent pipelines independently converge. A cross-artifact
consistency check *before* implementing is the one thing some of them add as a
stage; here it lives inside `executing-plans`, which reads the plan and argues
with it before task 1.

## Entry — the first stage depends on the input, not on the numbering

The numbers are a dependency order, not an arrival order. Stage 1 is not always
where a problem enters. Route on the shape of what the user said:

| The user gives you | Enter at | Because |
|---|---|---|
| An idea, a direction, "what if we…" | **2 `brainstormer`** | There is nothing to scope yet. Scoping an unchosen approach produces a brief you throw away |
| A named change with unstated scope ("add X", "support Y") | 1 `task-brief` | The approach is settled; the risk is scope, not direction |
| A question needing outside evidence | `research` | Neither design nor scope can be decided on a guess |
| Something broken | `systematic-debugging` | Diagnosis precedes everything, including the brief |
| A repo suspected of slop, at any stage | 6 `no-slop` | Slop accumulates across sessions, so no diff review sees it |
| An approved spec | 3 `writing-plans` | Design is done |
| An approved plan | 4 `executing-plans` | — |
| A finished change | 5 `verifying-work` | — |
| Work that landed on a branch while the environment still serves the old version | 9 `releasing` | Delivery is done; only the release is outstanding |

`brainstormer` before `task-brief` is the common case for open work, and both
orders are correct for their own input — established pipelines disagree about
which comes first, and it resolves by input shape rather than by picking a
winner. Entering at 2 does not skip the brief so much as absorb it: the spec
carries the scope a brief would have carried.

## Not every stage every time

The chain is a dependency order, not a checklist. Skip what the problem does not
need — a one-line fix needs 7 and 8, nothing else. Three rules bind regardless:

- **Stage 5 is never skipped when a completion claim is about to be made.** That
  is what the claim means.
- **Stages 8 and 9 each require their own human yes**, and stage 9's is per
  target. No skill can grant either.
- **Stage 10 closes every unit of work**, including ones that skipped everything
  else. Unrecorded work is indistinguishable from work that never happened.

## Two shapes

**Linear** — the table above, top to bottom. Correct when the done-check is
known before you start.

**Loop** — for work with no fixed end state (an experiment programme, a research
direction). Stages 1-3 run once to set direction, then stages 4-5 become two
nested loops inside `executing-plans`:

- *inner*: hypothesis → lock the protocol in git → run → sanity-check → record
- *outer*, every 5-10 inner passes: synthesise, then decide **DEEPEN**,
  **BROADEN**, **PIVOT** or **CONCLUDE**

CONCLUDE re-enters the line at stage 6. A loop declares its termination
criterion before the first pass.

## Handoffs

```
   1 task-brief ─────▶ 2 brainstormer ─────▶ 3 writing-plans
        │                     │                     │
        │                     │       [human yes]   ▼
        └─────────────────────┴────────────▶ 4 executing-plans
                                                    │
                                                    ▼
                                             5 verifying-work
                                                    │
                                                    ▼
                                                6 no-slop
                                                    │
                                      [human yes]   │
                                                    ▼
                                              7 code-review
                                                    │
                                      [human yes]   ▼
                                               8 delivering
                                                    │
                                      [human yes]   ▼
                                                9 releasing ──── no deploy target ┐
                                                    │                             │
                                                    ▼                             │
                                         10 knowledge-manager ◀───────────────────┘

   entered from any stage, returning to it:
     research               — needs outside evidence
     systematic-debugging   — something failed, incl. a red smoke check
                              (stage 9 rolls back first, then enters here)
```

`task-brief` branches two ways: straight to the change when the six fields are
filled, or to `brainstormer` when one could not be. **Never to `writing-plans`** —
stage 3 consumes an approved spec (see the Consumes column) and six lines is not
one, which is why the diagram above draws no arrow between them.

Every skill states its own mandatory validator and terminal handoff in its
`## Routing` section. Where this diagram and a skill disagree, the skill wins —
and one of them is a bug.

## Standing invariants

They hold at every stage, and each is enforced by a mechanism, not by good
intentions:

| Invariant | Enforced by |
|---|---|
| Never report a check as passing that was not run | `verifying-work` HARD-GATE |
| Never push, merge, publish or deploy without explicit approval | `delivering` HARD-GATE, `releasing` HARD-GATE, `pre-commit/02-branch-guard.py` |
| Never spend money on an unattended cloud command | `pre-deploy/01-spend-guard.py` — denies, never asks |
| Never call a release live on the deploy tool's exit code | `releasing` mandatory smoke check |
| Never deliver an unreviewed change | `code-review` over the branch at the push/PR boundary. Commits below that are unreviewed `wip:` checkpoints by design |
| Never auto-commit a secret, a red suite, or onto a protected branch | `post-run/06-artifact-autocommit.py`, enforced inline — its commits never reach `PreToolUse` |
| Never commit secrets | `pre-commit/01-secret-scan.py` |
| Never leave a unit of work unrecorded | `knowledge-manager`, invoked deliberately — no hook prompts for it |
| Never put AI attribution in git history | `_hooklib.AI_ATTRIBUTION_PATTERNS`, checked inline by the auto-commit |

## Where state lives between stages

`TASK.md` (1 `task-brief`) · `docs/specs/` (2 `brainstormer`) · `docs/plans/`
(3 `writing-plans`, ticked through 4 `executing-plans`) · `docs/research/`
(`research`, any stage) · `ISSUES.md` (`systematic-debugging`, and
9 `releasing` when a rollback fired) · `LOG.md`, `HANDOFF.md`, `MEMORY.md` and
`decisions/` (10 `knowledge-manager`).

`HANDOFF.md` is the only place a rollback command survives the session that
deployed. 9 `releasing` produces the rollback command and
10 `knowledge-manager` writes it down — which is what makes the release
reversible tomorrow rather than only for the rest of this session.

Chat is not the storage layer. A finding that stays in the conversation is lost
at the next context reset.

## Parallelism

Subagents in `.claude/agents/` let a stage fan out. They are dispatched by
the stage's own skill, never by this file, and **only when the user has asked
for subagents** — otherwise the stage does the work itself.

`Explore.md` sits alongside them but is not one of them: it overrides the
built-in `Explore` agent so exploration runs on a cheaper model, and the harness
invokes it directly rather than any skill dispatching it.

| Stage | Agent | Fans out over |
|---|---|---|
| Research (any) | `source-digger` | one per source; 3-5 at once |
| Diagnose (any) | `failure-investigator` | one per *independent* failure |
| 7 Review | `diff-reviewer` | one per angle: correctness, security, test-quality, scope |
| 4 Execute | `task-implementer` | one task at a time — never two |

Two rules hold across all four. **Dispatch in one message to run concurrently**;
one per message is sequential. And **hand artifacts over as file paths, never
pasted** — anything pasted into a dispatch stays in the dispatcher's context for
the rest of the session.

What never delegates: the sign-off in 7 `code-review`, the approval in
8 `delivering`, and any judgement about whether the work is done. An agent
reporting success is not evidence; the diff is.

Stage numbers in this file's prose are written as `N \`owner\`` on purpose, not as
a bare "stage N". `tools/test_process_router.py` checks every one of them against
the chain table, and it only can when the owner is named beside the number. Bare
references drift silently when a stage is inserted.

## Domain genericity

The stages are domain-free by construction — nothing above mentions code. What
differs per domain is *method inside a stage*, and that belongs in a pack file
under the owning skill (`references/<domain>.md`), never in a new skill and
never in the stage list. Adding a domain must not add a stage.

Stage 8 is where this is load-bearing rather than aspirational. Vercel, Render,
Fly, Kubernetes and a package registry are five domains, not five stages: the
shape — detect the target, state what cannot be undone, deploy, smoke, roll back
— is identical across all of them, and `releasing` carries only that shape. Any
platform's commands go in `.claude/skills/releasing/references/<platform>.md`.
A `if vercel: … elif render: …` branch inside `SKILL.md` is the failure mode
this rule exists to prevent; it grows without bound and every project pays for
the platforms it does not use.

## Adding to the chain

**`skill-authoring` owns the procedure. Read it, not this section** — it carries
the file list, the template and the constraints, and `tools/new_skill_check.py <name>`
adjudicates.

What stays here is the one fact that belongs to the chain rather than to
authoring: **a new skill is invisible until five files know about it, and nothing
errors when one is missing.** `new_skill_check.py` names all five; listing them
here too would make it a sixth file to edit when the wiring changes.

Before adding one, check whether the stage is genuinely unowned. **An unowned
gate is the clearest evidence a stage is missing** — a hook that denies something
no skill is responsible for, or an approval nobody's `## Routing` mentions.
Everything short of that belongs in a `references/` pack file under the skill
that already owns the stage.
