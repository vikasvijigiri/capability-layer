---
name: task-brief
description: Turn a vague request into a bounded, actionable brief. Triggers include "add X", "can we support Y", "users should be able to", "make it so that", "we need a way to", "track this bug". Do NOT use for a direct question, work already scoped, a one-file change with a stated goal, or an unsettled approach (brainstormer). Use this whenever work is named but unscoped, even if the user does not ask.
when_to_use: when a clear brief is needed for work
effort: medium
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob
---

# Task Brief

Turns "can we support multiple speakers?" into six lines someone could act on
without re-reading the chat. Narrow by design: it produces `TASK.md`. It does not plan, implement, or verify.

Cap visible output at ~500 tokens. The brief is six lines, not six paragraphs.

<HARD-GATE>
**Do not ask the user to approve the brief.** The chain has exactly two gates and
this is not one of them: state the six fields, write `TASK.md`, and continue.

Every field filled by inference rather than by the user's words must be marked
`(inferred)` in `TASK.md`. That is what replaces the approval -- the user reads
one artefact instead of answering a dialogue, and an assumption that was never
stated is visible rather than silently blessed. A brief with more inferred fields
than stated ones is the signal to stop and say so in one line, not to ask.
</HARD-GATE>

## Skip it when

The ask is a direct question, a one-word reply, a continuation of an approved
brief, or a change so small the brief costs more than the work. Say "too small
for a brief" in one line and just do it. A brief that is overhead stops being
read.

## Steps

**1. Restate verbatim.** Record the ask in the user's own words, unedited. Every
later field compresses this line; keeping the original is what makes drift
visible.

**2. Verify before you fill.** Every claim is a hypothesis, including the user's.
Use `Grep`/`Glob`/`Read` on the cheap ones: do the named files, functions,
commands, config keys and error strings exist? Does the described behaviour
match the code? Sort into **confirmed** / **disputed** / **unverifiable** and
carry any disputed item into the brief explicitly — a brief on a wrong premise
is worse than none, because it looks approved. Lightweight lookups only; if
scoping needs real root-cause work, say so and stop rather than absorbing
another job.

**3. Draft the six lines.**

    Goal:         the one outcome, in a sentence.
    Constraints:  what it must (and must not) do. Stack, perf, style, security.
    Inputs:       what the agent starts with. Files, data, an API, an example.
    Outputs:      what exists when it's finished. Files, endpoints, behavior.
    Done-check:   the concrete test that proves it works.
    Out-of-scope: what NOT to touch, so it doesn't wander.

- **Fill only from what was said or verified.** An unstated field stays blank. A
  guessed field is worse than an empty one — it gets approved as if the user had
  said it.
- **Done-check must be runnable.** `python tools/test_hooks.py exits 0` and
  `POST /session returns 201 with an id` are checks. "It works", "tests pass",
  "performance is better" are not.
- **Out-of-scope is never blank here.** Name the adjacent thing you could
  plausibly touch and won't.

**4. Score confidence, then proceed.** 0-100: how much of the six could
you fill without guessing? Weight down hard for a missing Constraints or
Out-of-scope — the two most often silently assumed — and further if Done-check
isn't concrete.

The score decides what you say, never whether you ask. **≥75** state the brief
and continue. **<75** state it, name the weak fields as `(inferred)`, and say in
one line that the scope is thin — then continue anyway. A low score is
information for the reader, not a request for input.

**5. Print the six lines as plain text.** Not inside a dialogue box; six fields
cannot be read in one. Mark every field filled by inference `(inferred)` — that
marking is what replaced the approval, so it is the one thing here that is not
optional.

**6. Write `TASK.md`, then hand off.** Write the six fields under its existing
names (`Goal` / `Input` / `Output` / `Constraints` / `Done Checks` /
`Out of Scope`) with `Status: In Progress`, carrying the `(inferred)` markers
through. Overwrite in place — it is current state, not history. Then take the
successor in `## Routing` in the same turn: a brief concrete enough to write is
concrete enough to build.

Do not hand the brief to `writing-plans`; that needs a design spec and
six lines is not one. If the work turns out to need real sequencing, the brief
was too big — say so and go to `brainstormer`.

## Red Flags — stop and re-read step 3

- "The Out-of-scope line is obvious, I'll leave it blank."
- "They clearly meant X, I'll put it in Outputs." A guess wearing an approved
  field's clothes.
- "Done-check: the tests pass." Name the command and its exit condition.
- "The scope is thin, I had better ask." State it `(inferred)` and continue.
- "They said the file is at X, so it's at X." Step 2 exists because that has
  been wrong before.

**Each of these means the brief is not ready. Go back to step 3.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Filling six fields from the prompt alone | The brief inherits the prompt's wrong premises and now looks approved |
| Briefing a two-line change | Overhead exceeds the work; a brief that is overhead stops being read |
| Asking the user to approve the brief | The chain has two gates and this is not one; mark inferred fields and continue |
| Treating a blank Outputs as "decide later" | It is the signal to stop and go to `brainstormer`, not a gap to fill |

## Next step — you MUST take it

The brief is not the deliverable; the work is. Once `TASK.md` is written, name
the successor and invoke it in the same turn. One of two, decided by the brief
itself:

1. **Six fields filled → do the change**, then `verifying-work`. The normal case.
2. **A field stayed blank because the approach is undecided → `brainstormer`.**
   Abandon the brief rather than guessing fields to keep it alive.

Stopping here is the chain's most common break: nothing watches for a finished
brief, so an un-handed-off one is simply forgotten.

`.claude/workflow.md` **Entry** owns which stage runs when, including why neither
option is `writing-plans`. It is stated there and not repeated here — this file
said it twice on its own until 2026-08-08, once in this section and once in
Routing, and two copies of one rule is how they come to disagree.

## Routing

- Mandatory validator: none, and no approval gate. The `(inferred)` markers in
  `TASK.md` are what a reader checks instead.
- Terminal handoff: one of the two above, named out loud.
- **Alternative to `brainstormer`, never a predecessor.** Brainstormer exists
  because the first idea becomes an anchor; a finished brief *is* that anchor,
  since Goal and Outputs commit to a solution shape.

## Success

`TASK.md` holds the six fields, every field filled by inference is marked
`(inferred)` there, and the Done-check is something a fresh session could run
without asking a question. No dialogue was opened to get there.
