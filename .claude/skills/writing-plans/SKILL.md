---
name: writing-plans
description: Turn named work into a bounded brief and an ordered, verifiable plan. Tasks in dependency order, the files each touches, the check that proves each, risks and rollback. Triggers include "add X", "build X", "we need a way to", "users should be able to", "make it so that", "write the implementation plan", "plan this out", "break this down", "what order should I build this in", "where do I start", "scope this", or the word PLAN. Do NOT use to implement it (executing-plans), to diagnose a failure (systematic-debugging), to choose between approaches (brainstormer), or for a direct question. Use this whenever work is named and needs scoping, even if the user does not ask.
when_to_use: Trigger when the user says add X, build X, we need a way to, users should be able to, make it so that, I want to support, can we have, write the implementation plan, plan this out, break this down, what order should I build this in, where do I start, how long will this take, scope this, or uses the word PLAN.
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob Task Bash EnterPlanMode ExitPlanMode AskUserQuestion
---

# Writing Plans

Owns the whole path from a named request to an approved plan: frame it, fetch
whatever is missing, then decompose it. The deliverable is one plan
document — not production code, scaffolding, migrations, tests, or
implementation edits.

**Framing and planning were once separate skills.** The boundary was deleted
rather than defended: the seam it guarded was where work fell through, because
nothing watched for a finished brief. Stage B is what replaces it.

## Hard boundary

- Read and inspect the repository; do not modify source, tests, configuration,
  or documentation other than the plan being created and `TASK.md`'s status line.
- Do not execute the plan while writing it. Do not invoke `executing-plans`,
  implement a task, or claim that the feature is built.
- Do not invent requirements. **Never guess.** Write
  `[NEEDS CLARIFICATION: <the exact question>]` inline where the answer belongs
  and keep going — a marker costs one line, a wrong assumption costs the build.
- **One dialogue, at Gate 1.** Framing asks nothing; see Stage A.

---

## Stage A — Frame the work

Six lines someone could act on without re-reading the chat.

<HARD-GATE>
**Do not ask the user to approve the brief.** The chain has exactly two gates and
this is not one of them: fill the six fields, put them in the plan, and continue into
Stage B.

Every field filled by inference rather than by the user's words must be marked
`(inferred)` in the plan. That is what replaces the approval — the user reads
one artefact instead of answering a dialogue, and an assumption that was never
stated is visible rather than silently blessed.
</HARD-GATE>

### Skip the whole skill when

The ask is a direct question, a one-word reply, a continuation of approved work,
or a change so small the brief costs more than the work. Say "too small to plan"
and just do it, then `verifying-work`. Overhead stops being read.

### A1. Restate verbatim, then verify

Record the ask in the user's own words, unedited — every later field compresses
that line, and keeping the original is what makes drift visible.

Then treat every claim in it as a hypothesis, including the user's, and check the
cheap ones with `Grep`/`Glob`/`Read`. `references/framing.md` owns the method and
what to do with a disputed premise. A brief built on a wrong one is worse than no
brief, because it looks approved.

### A2. Draft the six fields

Use these exact names — they carry unchanged into the plan header in A3, so a
renamed or re-pluralized field reads fine to a person and matches nothing a
later reader greps for.

    Goal:         the one outcome, in a sentence.
    Constraints:  what it must (and must not) do. Stack, perf, style, security.
    Input:        what the agent starts with. Files, data, an API, an example.
    Output:       what exists when it's finished. Files, endpoints, behavior.
    Done Checks:  the concrete test that proves it works.
    Out of Scope: what NOT to touch, so it doesn't wander.

- **Fill only from what was said or verified.** An unstated field stays blank. A
  guessed field is worse than an empty one — it gets approved as if the user had
  said it.
- **Done Checks must be runnable.** `<the suite that covers it> exits 0` and
  `POST /session returns 201 with an id` are checks. "It works", "tests pass",
  "performance is better" are not.
- **Out of Scope is never blank.** Name the adjacent thing you could plausibly
  touch and won't.

### A3. The brief goes in ONE place — the plan file

Write the six fields into the plan document's header (C4), carrying the
`(inferred)` markers through. Nowhere else.

**Do not print them in the reply, and do not copy them into `TASK.md`.** They
were living in three places at once — terminal, `TASK.md`, plan — so a reader
saw the same six fields three times and every later edit had to hit all three or
drift. `TASK.md` keeps a one-line status pointing at the plan; the plan holds
the brief; Gate 1 shows the plan. One artefact, read once.

Nothing breaks by moving them. `analyze.py` requires its headings in the **plan**
(`**Goal:**`, `**Risk:**`, `## File map`, `## Tasks`); `_hooklib.declared_paths`
reads `TASK.md` only for `- Create:`/`- Modify:` lines. `CLAUDE.md` claimed
three tools parsed the six fields out of `TASK.md` — none does, and that claim
is the reason the duplication survived.

---

## Stage B — Fetch what is missing, by dispatch

**A blank field is a signal, not a gap to fill.** When Stage A could not fill
one, go and get the answer rather than guessing it or handing back an unfinished
brief. Dispatch is automatic and needs no instruction from the user: invoke,
wait for the artifact, resume at A2 with the field filled.

| What Stage A could not fill | Invoke | Resume when |
|---|---|---|
| **Goal or Output blank because the approach is undecided** | `brainstormer` | `docs/specs/` holds a chosen design |
| A constraint turns on outside evidence — prior art, a library's real behaviour, whether it is possible at all | `research` | `docs/research/` holds the finding |
| The work touches a user-facing surface with no design contract | `designer` | `DESIGN.md` exists |
| The repository is unread and the brief would be written against a guess | `repo-recon` | `docs/recon/` holds the map |
| A current failure blocks framing, and its cause is unknown | `systematic-debugging` | the root cause is in `ISSUES.md` |

Three rules that keep this from becoming a loop:

- **Dispatch once per blank field.** A second dispatch on the same field means
  the answer is not discoverable, so it becomes a `[NEEDS CLARIFICATION]` marker
  for Gate 1 instead.
- **`brainstormer` outranks the brief.** If the approach is open, invoke it
  *before* filling the six fields — a finished brief commits Goal and Output to one
  solution shape, and that anchor is what stage 2 exists to prevent. Everything
  else here can run against a written brief.
- **Never dispatch to avoid deciding.** If the repository answers the question,
  read the repository.

### Score confidence, then proceed

Score 0–100 how much of the six you filled without guessing, by the method in
`references/framing.md`. **The score decides what you say, never whether you
ask** — below 75, name the weak fields `(inferred)`, say in one line that the
scope is thin, and continue anyway.

---

## Stage C — Plan

### C1. Enter plan mode, then read the input and the repository

**Call `EnterPlanMode` first.** Planning is read-only work and this is the stage
that does it, so the skill puts the session there rather than waiting to be put
there. The tool raises its own consent prompt — that is the user's say, and it
costs one click instead of remembering to pick a mode before asking for work.

If the session is already in plan mode, skip it and carry on.

Announce: "I'm using the writing-plans skill to create the implementation plan."

Read the brief and any spec completely, and confirm it describes **one coherent
deliverable** — if it spans subsystems that could be built and verified
separately, stop and recommend separate plans. Then read the code: existing
responsibilities, extension points, test seams, generated files that must not be
edited, and known risks. Do not plan from filenames or from the brief alone.

For a material feature or architectural change, apply
`references/artifact-review.md` to the spec first. A REVISE verdict returns to
Stage B; do not plan around an independently identified gap. For cross-cutting
boundaries, dispatch `architecture-reviewer` — it reports risks, this skill keeps
the plan and the gate.

### C1b. Ask what this repository already knows

Before the file map hardens, query the durable knowledge for the paths you are
about to touch:

    python tools/memory.py --paths <the files you expect to change>
    python tools/memory.py --plan <the plan>      # once the map exists

It reads `MEMORY.md`, `ISSUES.md` and `decisions/` and returns entries that name
those files or their directory. **State what came back, including when nothing
did** — "nothing recorded about these files" is a finding a reader can act on;
silence is indistinguishable from not having looked.

This was a write-only habit for a long time: every unit of work wrote to
`MEMORY.md` and nothing ever read it, so a convention learned in one session
could not change a plan written in the next. A knowledge store nobody queries is
worse than none, because writing to it feels like the work is being retained.

A returned entry is **evidence, not an order.** An ADR that settled a question
still settles it; a convention recorded before the thing it describes was
rewritten may be rot. `python tools/memory.py --stale` names entries whose paths
or counts no longer match the tree — if one you are relying on shows up there,
fix the entry as part of this work rather than planning against it.

### C2. Freeze the file map

Before defining tasks, state for every file the implementation may touch whether
it is created, modified, moved or deleted, and what it owns afterwards. Every
planned file needs a reason; every requirement in the brief maps to a file or to
an explicit verification step. Prefer focused changes that follow the existing
structure — a cleaner layout is not a reason to refactor.

### C3. Decompose into executable tasks

Order tasks by dependency: foundations, then behavior, then integration. Split a
task whenever a reviewer could accept one part and reject another.

**`references/task-decomposition.md` owns the task block's required shape** and
the three rules `tools/parallel_groups.py` enforces on it. Read it before writing
the first task. The one thing that decides whether the plan can be scheduled at
all:

    python tools/parallel_groups.py <this plan>

It **refuses a plan rather than guessing**: an undeclared path is one the
scheduler cannot see, and a dependency written as prose reads as independence,
which dispatches ordered work concurrently. Entirely serial is a fine answer.

Use test-first sequencing where behavior can be tested. Replace every vague step
("add validation", "handle edge cases") with the exact file, symbol, test input,
expected result and command. No task commits, pushes, merges or deploys — those
are later stages.

### C4. Write the plan document

Save it at `docs/plans/YYYY-MM-DD-<feature-name>.md`.

**`references/plan-document.md` owns the format** — the required header, the
`**Slug:**` field `tools/resume.py` keys every derived fact off, the constitution
gate, the two markers the machinery parses, and the six-point self-review. Read
it before writing the file.

Two things from it that decide whether the plan is even reviewable, so they are
stated here too:

- **`[NEEDS CLARIFICATION: q]` outranks approval.** While any marker remains the
  derived state is `WAITING_PLAN_APPROVAL`, whatever else the file says.
- **Run `python tools/analyze.py --slug <slug>` before presenting anything.** It
  finds missing sections, unresolved markers, unjustified gate exceptions, tasks
  with no verification command, and `Modify` targets that do not exist.

## Completion and handoff

The skill is complete only when the plan is saved, self-reviewed, and presented
for the plan approval gate. State the plan path, task count, key assumptions and
known risks.

<!-- GATE 1: plan approval. The chain has two; see .claude/workflow.md. -->
**Gate 1 is `ExitPlanMode`, and it is the only approval mechanism here.**

That tool's contract *is* this gate — it "inherently requests user approval" and
says not to pair it with a second question. **`ExitPlanMode` refuses outside plan
mode**, which is why C1 enters it: a gate that only works when the session
happened to start somewhere particular is not a gate.

**The approval is `ExitPlanMode` and nothing else.** `AskUserQuestion` must never
carry it — two mechanisms mean the plan is approved twice and one of them is
theatre. Using it to *clarify an approach* while planning is fine and is what the
tool's own documentation recommends; the ban is on the approval, not the tool.

**Every `[NEEDS CLARIFICATION]` marker goes into the plan body before the exit**,
beside the paragraph its answer belongs to. One batch, at the gate — scattered
questions are what turned two gates into nine, and they interrupt when the answer
is least informed.

All three outcomes stay reachable. On approve, write `## Approved` into the plan
— that exact heading, because `tools/resume.py` derives the unit's state from it
and a paraphrase leaves an approved plan reading as unapproved. Revise and reject
record the user's own words verbatim.

Plan mode is read-only apart from the plan, so **`TASK.md`'s one-line status is
written immediately after the exit** — ownership does not move, only the moment.

`references/plan-mode.md` owns all of it: the one-tool rule, the three outcomes,
why the status line moved, and the one thing no skill can do — switch permission mode.
`references/plan-document.md` owns the rejection block's format.

After the user approves, invoke `executing-plans` and pass it the plan path.
Until approval is explicit, stop here.

## Red Flags — stop and re-read Stage A

- "The Out of Scope line is obvious, I'll leave it blank."
- "They clearly meant X, I'll put it in Output." A guess wearing an approved
  field's clothes.
- "Done Checks: the tests pass." Name the command and its exit condition.
- "The scope is thin, I had better ask." State it `(inferred)` and continue.
- "They said the file is at X, so it's at X." A1 verifies because that has
  been wrong before.
- "The approach is open, but I'll write the brief anyway and let the plan sort it
  out." That is the anchor Stage B exists to prevent; dispatch `brainstormer`
  first — once the six fields exist, the brief is already the anchor.
- "This is a two-line change, but I'll plan it properly." Overhead exceeds the
  work. Say "too small to plan" and do it.

## Next step — you MUST take it

The terminal state is invoking `executing-plans` after the user approves the
saved plan. Pass the plan path. Do not implement any task in this skill.

The one branch: work that turned out **too small to plan** skips the plan and
the gate entirely — do the change, then `verifying-work`. Say which branch you
took out loud.

## Routing

- Mandatory validator: `python tools/analyze.py --slug <slug>`, then the
  self-review. No implementation suite runs — this produces a plan, not code.
- Independent validator: `references/artifact-review.md` for material briefs and plans.
- Entered directly from a named request — this skill owns framing.
  `.claude/workflow.md` §Entry owns when that happens.
- Dispatches `brainstormer`, `research`, `designer`, `repo-recon` and
  `systematic-debugging` per the Stage B table, plus `architecture-reviewer`
  per C1 for cross-cutting boundaries. None of those is a handoff — each
  returns here.
- Terminal handoff: `executing-plans`, only after the plan approval gate.

## Success

- The plan holds the six fields, under the exact names given in A2, every
  inferred one marked `(inferred)`, and they appear nowhere else.
- A dated plan exists under `docs/plans/` whose `**Slug:**` matches the branch.
- Every open question was a marker, and every marker was answered at the gate.
- No dialogue was opened before Gate 1, and execution did not start before it.