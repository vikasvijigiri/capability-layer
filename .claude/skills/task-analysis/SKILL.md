---
name: task-analysis
description: Turn named work into a bounded brief and an ordered, verifiable plan. Tasks in dependency order, the files each touches, the check that proves each, risks and rollback. Triggers include "add X", "build X", "we need a way to", "make it so that", "write the implementation plan", "plan this out", "break this down", "where do I start", "scope this", or the word PLAN. Do NOT use to implement it (implementation), to diagnose a failure (debugging), to choose between approaches (architecture), or for a direct question. Use this whenever work is named and needs scoping, even if the user does not ask.
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Task Bash EnterPlanMode ExitPlanMode AskUserQuestion
---

# Task Analysis

Owns the whole path from a named request to an approved plan: intake and
state, a genuine-task check, framing, fetching what is missing, then
decomposing. The deliverable is one plan document — not code, scaffolding,
migrations, tests, or implementation edits. Built from the former
`writing-plans` skill, compressed — see `references/plan-format.md` for
the templates this body used to inline.

**Maps to Notion §1's pre-execution pipeline**, so nothing here is a new
concept, only a name: INTAKE+STATE is `tools/resume.py` (below); the TASK
GATE is Stage A0; TASK ANALYZER is Stage A's six fields plus the E0-E5
estimate `prompt-intake/01-entry-classifier.py` already computed for this
turn; CAPABILITY/EXECUTION ROUTER is Stage B's dispatch table plus the
Runtime Decision Matrix below.

## Hard boundary

- Read and inspect the repository; modify only the plan being created and
  `TASK.md`'s status line.
- Do not execute the plan while writing it, invoke `implementation`, or claim
  the feature is built.
- Never guess. Write `[NEEDS CLARIFICATION: <question>]` inline where the
  answer belongs and keep going — a marker costs one line, a wrong assumption
  costs the build.
- **One dialogue, at Gate 1.** Framing asks nothing; see Stage A.

---

## Stage A0 — Intake, state, and the genuine-task gate

**Reuse before retrieve, first.** Before reading anything else: has this
session already established the fact you're about to look up — a file
already read, a command already run, a question already answered? Check
context before a tool call, not after. `python tools/bench.py`'s
duplicate-rate line is what this omission costs when skipped.

**State.** `python tools/resume.py` derives what unit of work this is from
git facts, before anything is framed — the INTAKE+STATE half of Notion §1.
Trust it over recollection, especially after a context reset.

**Genuine-task gate.** Is this actually actionable work with a done-state,
or a question, a reply, or nothing? `prompt-intake/01-entry-classifier.py`
already answered this for the current turn (`entry-direct`/silent = not a
task for this skill; `entry-small`/`entry-unframed`/`entry-open` = it is) —
read its rendered block rather than re-deriving the same classification by
eye.

## Stage A — Frame the work

Six lines someone could act on without re-reading the chat.

<HARD-GATE>
Do not ask the user to approve the brief — the chain has two gates and this is
not one. Fill the six fields, put them in the plan, continue into Stage B.
Every field filled by inference rather than the user's words must be marked
`(inferred)` — that is what replaces the approval.
</HARD-GATE>

Skip the whole skill when the ask is a direct question, a one-word reply, a
continuation of approved work, or a change so small the brief costs more than
the work. Say "too small to plan" and just do it, then `testing`.

**A1. Restate, then verify.** Record the ask in the user's own words, unedited
— every later field compresses it, and keeping the original makes drift
visible. Treat every claim as a hypothesis, including the user's: check the
cheap ones with `Grep`/`Glob`/`Read` and sort confirmed / disputed /
unverifiable. A brief built on a wrong premise is worse than none, because it
looks approved. Lightweight lookups only — real root-cause work is a
`debugging` dispatch, not this skill absorbing another job.

**A2. Draft the six fields**, exact names — they carry unchanged into the plan
header at C4:

    Goal:         the one outcome, in a sentence.
    Constraints:  what it must (and must not) do. Stack, perf, style, security.
    Input:        what the agent starts with. Files, data, an API, an example.
    Output:       what exists when it's finished. Files, endpoints, behavior.
    Done Checks:  the concrete, runnable test that proves it works --
                  `<suite> exits 0` or `POST /session returns 201 with an id`.
                  "It works" or "tests pass" is not a check.
    Out of Scope: what NOT to touch, so it doesn't wander. Never blank.

Fill only from what was said or verified. An unstated field stays blank; a
guessed field is worse than an empty one — it gets approved as if said.

**Score confidence** 0-100: how much of the six you filled without guessing.
Weight down hard for a missing Constraints or Out of Scope, further if Done
Checks is not a runnable command. The score decides what you say, never
whether you ask — below 75, name the weak fields `(inferred)`, say in one line
that the scope is thin, and continue anyway.

**A3. The brief goes in ONE place — the plan file (C4).** Not the reply, not
`TASK.md` (which keeps a one-line status pointer at the plan).

---

## Stage B — Fetch what is missing, by dispatch

A blank field is a signal, not a gap to fill by guessing. Dispatch is
automatic and needs no instruction: invoke, wait for the artifact, resume at
A2 with the field filled.

| What Stage A could not fill | Invoke | Resume when |
|---|---|---|
| Goal or Output blank, approach undecided | `architecture` (options-comparison) | `docs/specs/` holds a chosen design |
| A constraint turns on outside evidence | `research` | `docs/research/` holds the finding |
| A user-facing surface with no design contract | `architecture` (design-contract) | `DESIGN.md` exists |
| The repository is unread | `repository-navigation` | `docs/recon/` holds the map |
| A current failure blocks framing | `debugging` | the cause is in `ISSUES.md` |

- **Dispatch once per blank field.** A second dispatch on the same field means
  the answer is not discoverable, so it becomes a `[NEEDS CLARIFICATION]`
  marker for Gate 1 instead.
- **`architecture`'s options-comparison outranks the brief** — if the
  approach is open, invoke it before writing the brief. A finished brief
  commits Goal and Output to one solution shape, and that anchor is what
  the dispatch exists to prevent.
- **Never dispatch to avoid deciding.** If the repository answers the
  question, read the repository.

### Runtime Decision Matrix (Notion §19) — upper guidance, not a quota

| Situation | Skills | Agents | Tool calls | Verification |
|---|---|---|---|---|
| Simple question | 0 | 0 | 0 | sanity |
| Simple code change | 1 | 0 | 1-2 | targeted |
| Debugging | 1-2 | 0-1 | 1-4 | targeted tests |
| Refactor | 1-2 | 0-1 | 2-5 | affected tests |
| Research | 1 | 0-2 | batched | evidence |
| Architecture | 1-2 | 0-2 | as needed | design review |
| Security change | 1-2 | 0-1 | as needed | security gates |
| Large feature | 2-4 | 2-5 | batched/parallel | multi-layer |

Escalation is evidence-driven, not complexity-driven: a long prompt does
not mean many agents, and a large repository does not mean reading all of
it. Use this to catch an execution graph that's grown past what the
situation actually calls for — not to justify padding one out.

---

## Stage C — Plan

**C1. Enter plan mode, then read the input and the repository.** Call
`EnterPlanMode` first — planning is read-only, so the skill puts the session
there itself rather than assuming it already is. If already in plan mode,
skip it. Announce: "I'm using the task-analysis skill to create the
implementation plan."

Read the brief and any spec completely; confirm it describes **one coherent
deliverable** — if it spans subsystems that could be built and verified
separately, stop and recommend separate plans. Then read the code: existing
responsibilities, extension points, test seams, generated files that must not
be edited, known risks. Do not plan from filenames or the brief alone.

For a material feature or architectural change, apply
`references/artifact-review.md` to the spec first. A REVISE verdict returns to
Stage B; do not plan around an independently identified gap. For cross-cutting
boundaries, dispatch `architect` — it reports risks, this skill
keeps the plan and the gate.

**C1a. Ground the plan in real patterns before inventing any.** Search the
repository for the convention the implementation should mirror, one example
per row with a `file:line` citation:

| Category | What to capture |
|---|---|
| Naming | File, function, type, command or script naming in the affected area |
| Error handling | How failures are raised, returned, logged, or degraded |
| Data access | Repository, service, query, or filesystem pattern |
| Tests | Location, framework, fixtures, assertion style |

State plainly when no similar code exists in the row — do not invent a pattern
to fill it.

**C1b. Ask what this repository already knows.**

    python tools/memory.py --paths <the files you expect to change>

Reads `MEMORY.md`, `ISSUES.md` and `decisions/` for entries naming those files
or their directory. **State what came back, including when nothing did** —
silence is indistinguishable from not having looked. `python tools/memory.py
--stale` names entries whose paths no longer match the tree — fix a stale one
you're relying on rather than planning against it.

**C2. Freeze the file map.** Before defining tasks, state for every file the
implementation may touch whether it is created, modified, moved or deleted,
and what it owns afterward. Every planned file needs a reason; every brief
requirement maps to a file or an explicit verification step. Prefer focused
changes that follow the existing structure — a cleaner layout is not a reason
to refactor.

**C3. Decompose into executable tasks.** Order by dependency: foundations,
then behavior, then integration. Split a task whenever a reviewer could
accept one part and reject another. Test-first where behavior can be tested.
Replace every vague step ("add validation", "handle edge cases") with the
exact file, symbol, test input, expected result, command. No task commits,
pushes, merges or deploys — those are later stages.

Every plan carries a `## Progress` block directly above `## Tasks`, one
checkbox per task, and each task follows the exact shape (Files/Dependencies/
Verification/etc.) in **`references/plan-format.md`** — read it before writing
the first task.

Run this before writing the first task, and again before presenting the plan
at Gate 1:

    python tools/parallel_groups.py <this plan>

It **refuses a plan rather than guessing**: an undeclared path is one the
scheduler cannot see; `Dependencies:` written as prose ("the store's read
API") or as a range ("1-8") reads as independence and dispatches ordered work
concurrently — write out every dependency number. A task touching a
migration, lockfile or CI config gets its own round automatically.

**C4. Write the plan document** at `docs/plans/YYYY-MM-DD-<feature-name>.md`
per **`references/plan-format.md`**'s exact header and Constitution-gate
templates.

Keep the plan self-contained. An engineer who has not participated in the
conversation should be able to execute each task without guessing what a
path, symbol, test, or dependency means.

**C5. Self-review before handoff.** Run the mechanical pass first — cheap,
and it finds what reading misses:

    python tools/analyze.py --slug <slug>

It reports missing sections, unresolved markers, unjustified gate exceptions,
tasks with no verification command, and `Modify` targets that do not exist —
note that a target created by an EARLIER task in the same plan will
correctly show as "does not exist" at analysis time; that is not a defect,
confirm it against `parallel_groups.py`'s ordering instead of "fixing" it.
Fix every genuine finding before spending a review on the plan.

Then apply `references/artifact-review.md` to the completed plan, against the
six fields from A2 — the actual goal/input the plan must satisfy. Treat its
verdict as independent evidence; do not silently repair a rejected plan in
the same pass as the review that rejected it.

**Self-review is capped at 2 iterations.** The pass above is iteration 1. On
REVISE, fix the named gaps, re-run `tools/analyze.py`, and re-apply
`artifact-review.md` — that is iteration 2. An APPROVED or APPROVED WITH
RECORDED RISK verdict on iteration 1 ends the loop immediately; iteration 2
only happens after a REVISE. A Stage B dispatch (fetching a genuinely
missing fact) does not count against the cap — the cap bounds re-review of
an already-drafted plan, not information-gathering.

On a **second** REVISE, stop iterating. A plan that still fails after being
told exactly what to fix twice is a disagreement worth surfacing at Gate 1,
not a defect this skill can out-think by trying a third time. Fold the
reviewer's finding into the plan as `[NEEDS CLARIFICATION: <finding,
verbatim>]` at the paragraph it concerns, state "self-review: 2/2,
unresolved — see marker" in the completion summary, and present at Gate 1
anyway — the marker is what keeps this honest rather than silently
downgrading REVISE to APPROVED.

Then review the completed plan against the brief, not memory:

1. Coverage — every requirement, acceptance criterion, and constraint has a
   task or verification step.
2. Ordering — no task consumes a file, symbol, schema, or interface that a
   later task creates.
3. File accuracy — every path exists or is explicitly marked for creation;
   symbols and neighboring patterns match the repository.
4. Testability — every behavior-changing task has a concrete test or check,
   with expected output and failure coverage where practical.
5. Completeness — no placeholders, hidden decisions, accidental scope, or
   production implementation disguised as plan prose.
6. Execution safety — irreversible actions, migrations, credentials, and
   external integrations have explicit constraints and rollback considerations.

Fix gaps before presenting. If a gap reveals the approach is unsettled, return
to Stage B rather than filling it by assumption.

## Completion and handoff

Complete only when the plan is saved, self-reviewed, and presented for the
plan approval gate. State the plan path, task count, key assumptions and
known risks.

<!-- GATE 1: plan approval. The chain has two; see .claude/workflow.md. -->
**Gate 1 is `ExitPlanMode`, and it is the only approval mechanism here.**

That tool's contract *is* this gate — it "inherently requests user approval"
and says not to pair it with a second question. **`ExitPlanMode` refuses
outside plan mode**, which is why C1 enters it. A prior version of this rule
claimed no tool could enter plan mode; that was false — `EnterPlanMode`
exists, and `ExitPlanMode`'s own refusal message names it.

**The approval is `ExitPlanMode` and nothing else.** `AskUserQuestion` must
never carry it — two mechanisms mean the plan is approved twice and one of
them is theatre. Using it to *clarify an approach* while planning is fine;
the ban is on the approval, not the tool.

**Every `[NEEDS CLARIFICATION]` marker goes into the plan body before the
exit**, beside the paragraph its answer belongs to. One batch, at the gate.

All three outcomes stay reachable:

| Outcome | Means |
|---|---|
| Approve | write `## Approved` — that exact heading, since `tools/resume.py` derives the unit's state from it — then hand off to `implementation` |
| Revise | rejected; the user's own words become the brief |
| Reject | the approach is wrong; return to `architecture` |

Revise and reject are recorded **verbatim** — `tools/loop.py` refuses to
re-present a plan body whose hash has not changed. Record the decision:

    python tools/chain.py --gate 1 --decision approve|revise|reject --reason "<their words>"

Plan mode is read-only apart from the plan, so **`TASK.md`'s one-line status
is written immediately after the exit**.

After the user approves, invoke `implementation` and pass it the plan path.
Until approval is explicit, stop here.

## Red Flags — stop and re-read Stage A

- "The Out of Scope line is obvious, I'll leave it blank."
- "They clearly meant X, I'll put it in Output." A guess wearing an approved
  field's clothes.
- "Done Checks: the tests pass." Name the command and its exit condition.
- "The scope is thin, I had better ask." State it `(inferred)` and continue.
- "The approach is open, but I'll write the brief anyway and let the plan
  sort it out." Dispatch `architecture` first — once the six fields exist,
  the brief is already the anchor.
- "This is a two-line change, but I'll plan it properly." Overhead exceeds
  the work. Say "too small to plan" and do it.
- "I already know the answer to that from earlier in this session, but I'll
  re-check it anyway." That is the duplicate-call cost Stage A0 exists to
  catch — reuse before retrieve.

## Next step — you MUST take it

The terminal state is invoking `implementation` after the user approves the
saved plan. Pass the plan path. Do not implement any task in this skill.

The one branch: work that turned out **too small to plan** skips the plan and
the gate entirely — do the change, then `testing`. Say which branch you took
out loud.

## Routing

- Mandatory validator: `python tools/analyze.py --slug <slug>`, then the
  self-review. No implementation suite runs — this produces a plan, not code.
- Independent validator: `references/artifact-review.md` for material briefs
  and plans.
- Entered directly from a named request — this skill owns framing.
  `.claude/workflow.md` §Entry owns when that happens.
- Dispatches `architecture`, `research`, `repository-navigation` and
  `debugging` per the Stage B table, plus `architect` per C1 for
  cross-cutting boundaries. None of those is a handoff — each returns here.
- Terminal handoff: `implementation`, only after the plan approval gate.

## Success

- The plan holds the six fields, under the exact names given in A2, every
  inferred one marked `(inferred)`, and they appear nowhere else.
- A dated plan exists under `docs/plans/` whose `**Slug:**` matches the branch.
- Every open question was a marker, and every marker was answered at the gate.
- No dialogue was opened before Gate 1, and execution did not start before it.
