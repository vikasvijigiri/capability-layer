# Workflow

The chain of skills that takes any problem — a feature, a bug, a research
question, a decision — from a rough ask to a delivered result.

Each stage names the skill that owns it. Read the skill, not this file, for how
a stage works; this file exists to say **which** skill and **what it hands on**.
An earlier ASCII sketch of this pipeline lived here until 2026-08-02 and is in
git history.

---

## The chain

Nine stages on the line, two entered from anywhere. One skill each — a stage
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
| 6 | Review | `code-review` | the pending change | findings, then a sign-off receipt |
| — | **Human approval** | — | the findings | a yes, in the conversation |
| 7 | Deliver | `delivering` | verified, reviewed work | merged / pushed / PR opened, or kept |
| — | **Human approval** | — | the target and the rollback | a yes, per target, in the conversation |
| 8 | Release | `releasing` | delivered work + a deploy target | the change serving at a named target, a quoted smoke check, a named rollback |
| 9 | Record | `knowledge-manager` | what happened | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `MEMORY.md`, `decisions/` |

Stage 8 is the only stage that is **skipped by absence rather than by judgement**:
a repo with no deploy target has nothing to release, and `releasing` says so and
hands straight to 9. Stages 7 and 8 are two acts, not one — merging changes a
repository, releasing changes what users are looking at right now, and an
approval for one is not an approval for the other.

Two stages are not positions on the line. They are entered from wherever the
need arises and return to the stage that called them:

| Stage | Owner | Entered when | Returns to |
|---|---|---|---|
| Research | `research` | any stage needs evidence from outside your own knowledge | whatever asked |
| Diagnose | `systematic-debugging` | anything fails or behaves unexplainably, at any stage | the stage that hit the failure |

### What this replaced, and why

Until 2026-08-02 this file listed **13 stages for 10 skills**, inherited from an
ASCII pipeline sketch. Four things were wrong with it, and the file contradicted
itself:

1. **The table and the handoff graph disagreed.** The table put Document (10)
   *before* Self-review (11) and Deliver (12); the graph below put
   `knowledge-manager` last. The skills implement the graph — `delivering`'s
   terminal handoff is `knowledge-manager` — so the table was simply wrong.
2. **"Optimise" was assigned to `code-review`, which cannot do it.** That
   skill's own text says "Do NOT use to fix what the review finds — report
   first, fix as separate work". A stage whose owner is forbidden from
   performing it has no owner. Simplification is work like any other: it gets a
   brief and goes round the line, or it is `/simplify` on a diff.
3. **Document (10) and Learn (13) were the same skill doing the same write.**
   `knowledge-manager` writes `LOG.md`, `HANDOFF.md`, `ISSUES.md` and
   `decisions/` in one pass, at the end. Two stages described one act.
4. **Ideate (2) and Design (5) were one conversation.** `brainstormer` diverges
   and converges and emits a single spec; nothing happens at the boundary
   between them.

The ordering here — plan → build → validate → review → deliver → record —
is what every pipeline consulted converges on: superpowers
(brainstorm → plan → execute → review → finish), spec-kit
(specify → plan → tasks → analyze → implement), BMAD (`plan` module then `ship`
module, retrospective last), and the agentic-SDLC literature, which places the
retrospective after review rather than before it.

One thing others do that this chain does **not** do as a stage: spec-kit runs
`analyze` — a cross-artifact consistency check of spec vs plan vs tasks —
*before* implementing, as well as verifying after. Here that check lives inside
`executing-plans` ("Before Task 1: read the plan and argue with it") rather than
as a stage of its own. If it ever needs to be its own gate, that is the argument
for it.

## Entry — the first stage depends on the input, not on the numbering

The numbers are a dependency order, not an arrival order. Stage 1 is not always
where a problem enters. Route on the shape of what the user said:

| The user gives you | Enter at | Because |
|---|---|---|
| An idea, a direction, "what if we…" | **2 `brainstormer`** | There is nothing to scope yet. Scoping an unchosen approach produces a brief you throw away |
| A named change with unstated scope ("add X", "support Y") | 1 `task-brief` | The approach is settled; the risk is scope, not direction |
| A question needing outside evidence | `research` | Neither design nor scope can be decided on a guess |
| Something broken | `systematic-debugging` | Diagnosis precedes everything, including the brief |
| An approved spec | 3 `writing-plans` | Design is done |
| An approved plan | 4 `executing-plans` | — |
| A finished change | 5 `verifying-work` | — |
| Work that landed on a branch while the environment still serves the old version | 8 `releasing` | Delivery is done; only the release is outstanding |

`brainstormer` before `task-brief` is the common case for open work, and both
orders are correct for their own input. Superpowers has no brief stage at all
and makes brainstorming mandatory before *any* creative work; spec-kit starts at
framing instead. The disagreement is real, and it resolves by input shape rather
than by picking a winner.

Entering at 2 does not skip the brief so much as absorb it: the spec carries the
scope a brief would have carried.

## Not every stage every time

The chain is a dependency order, not a checklist. Skip what the problem does not
need — a one-line fix needs 6 and 7, nothing else. Three rules bind regardless:

- **Stage 5 is never skipped when a completion claim is about to be made.** That
  is what the claim means.
- **Stages 7 and 8 each require their own human yes**, and stage 8's is per
  target. No skill can grant either.
- **Stage 9 closes every unit of work**, including ones that skipped everything
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
                                              6 code-review
                                                    │
                                      [human yes]   ▼
                                               7 delivering
                                                    │
                                      [human yes]   ▼
                                                8 releasing ──── no deploy target ┐
                                                    │                             │
                                                    ▼                             │
                                          9 knowledge-manager ◀───────────────────┘

   entered from any stage, returning to it:
     research               — needs outside evidence
     systematic-debugging   — something failed, incl. a red smoke check
                              (stage 8 rolls back first, then enters here)
```

`task-brief` branches: to `brainstormer` when the approach is open, to
`writing-plans` when it is settled, straight to the change when it is smaller
than a plan.

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
| Never leave a unit of work unrecorded | `knowledge-manager`. No hook prompts for it since 2026-08-02 |
| Never put AI attribution in git history | `_hooklib.AI_ATTRIBUTION_PATTERNS`, checked inline by the auto-commit |

## Where state lives between stages

`TASK.md` (1) · `docs/specs/` (2) · `docs/plans/` (3, ticked through 4) ·
`docs/research/` (`research`, any stage) · `ISSUES.md` (`systematic-debugging`,
and 8 when a rollback fired) · `LOG.md`, `HANDOFF.md`, `MEMORY.md` and
`decisions/` (9).

`HANDOFF.md` is the only place a rollback command survives the session that
deployed. Stage 9 writing it down is what makes stage 8 reversible tomorrow.

Chat is not the storage layer. A finding that stays in the conversation is lost
at the next context reset.

## Parallelism

Four subagents in `.claude/agents/` let a stage fan out. They are dispatched by
the stage's own skill, never by this file, and **only when the user has asked
for subagents** — otherwise the stage does the work itself.

| Stage | Agent | Fans out over |
|---|---|---|
| Research (any) | `source-digger` | one per source; 3-5 at once |
| Diagnose (any) | `failure-investigator` | one per *independent* failure |
| 6 Review | `diff-reviewer` | one per angle: correctness, security, test-quality, scope |
| 4 Execute | `task-implementer` | one task at a time — never two |

Two rules hold across all four. **Dispatch in one message to run concurrently**;
one per message is sequential. And **hand artifacts over as file paths, never
pasted** — anything pasted into a dispatch stays in the dispatcher's context for
the rest of the session.

What never delegates: the sign-off in stage 6, the approval in stage 7, and any
judgement about whether the work is done. An agent reporting success is not
evidence; the diff is.

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

A new skill needs three things or it is invisible:

1. `.claude/skills/<name>/SKILL.md`, with frontmatter `name:` matching the
   directory.
2. A `## <name>` entry with a `Keywords:` line in
   `.claude/routing/process-skills.md`. `tools/test_process_router.py` fails
   the build without it.
3. A row in this file, naming what it consumes and produces.

Before adding one, check whether the stage is genuinely unowned. Eleven process
skills is at the ceiling every comparable repo converges on; growth belongs in
pack files. See `docs/research/2026-08-02-generic-pipeline-skillset.md`.

`releasing` was added on 2026-08-02 as the eleventh, and it passed that test:
`delivering`'s menu offered merge, PR and keep, none of which is a deploy, while
`pre-deploy/01-spend-guard.py` had been firing on cloud CLIs with no skill
owning the act it guards. An unowned gate is the clearest evidence a stage is
missing. Prior art agrees on the shape but not the genericity — 1,220 public
repos ship a `.claude/skills/deploy*`, and the two representative ones are
[deployment-patterns](https://github.com/affaan-m/everything-claude-code/blob/main/skills/deployment-patterns/SKILL.md)
(a content pack: Dockerfiles and k8s probes — belongs in `references/`) and
[deployment-sop](https://github.com/bybren-llc/safe-agentic-workflow/blob/main/.claude/skills/deployment-sop/SKILL.md)
(the right process spine, hardcoded to one vendor stack).
