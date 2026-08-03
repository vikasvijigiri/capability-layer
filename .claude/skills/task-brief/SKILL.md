---
name: task-brief
description: Use when a request names work but leaves the goal, constraints or scope unstated, and the approach is already settled. Triggers include "add X", "can we support Y", "users should be able to", "make it so that", or a bug report worth tracking. Do NOT use for a direct question, work already scoped, a one-file change whose goal is already stated, or an unsettled approach (brainstormer).
effort: medium
model: sonnet
---

# Task Brief

Turns "can we support multiple speakers?" into six lines someone could act on
without re-reading the chat. Narrow by design: it produces an approved brief and
`TASK.md`. It does not plan, implement, or verify.

Cap visible output at ~500 tokens. The brief is six lines, not six paragraphs.

<HARD-GATE>
Nothing is written and no work starts until the user approves the brief.
Presenting the brief and acting on it in the same turn is the failure this skill
exists to prevent.
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

**4. Score confidence, then ask or present.** 0-100: how much of the six could
you fill without guessing? Weight down hard for a missing Constraints or
Out-of-scope — the two most often silently assumed — and further if Done-check
isn't concrete. **≥75** present the brief; **<75** one round of
`AskUserQuestion` targeted at the blank fields only, never a generic "tell me
more", then redraft.

**5. Gate it.** Print the six lines as plain text first — six fields cannot be
read inside a dialogue box. Then `AskUserQuestion`:

- **Approve** — state what approving commits to, and name every field filled by
  inference rather than by the user's words.
- **Refine** — nothing written; redraft and re-present. May run more than once.
- **Cancel** — nothing written, `TASK.md` untouched.

Free-text **Other** is always appended, which is how one field gets corrected
without rejecting the whole brief. A plain "yes" in chat is approval — the
dialogue is the default, not a hoop.

**6. Write `TASK.md`, then stop.** On approval only, write the six fields under
its existing names (`Goal` / `Input` / `Output` / `Constraints` / `Done Checks` /
`Out of Scope`) with `Status: In Progress`. Overwrite in place — it is current
state, not history. An approved brief has exactly one destination: execute
directly against the Done-check. A brief concrete enough to approve is concrete
enough to build.

Do not hand an approved brief to `writing-plans`; that needs a design spec and
six lines is not one. If the work turns out to need real sequencing, the brief
was too big — say so and go to `brainstormer`.

## Red Flags — stop and re-read step 3

- "The Out-of-scope line is obvious, I'll leave it blank."
- "They clearly meant X, I'll put it in Outputs." A guess wearing an approved
  field's clothes.
- "Done-check: the tests pass." Name the command and its exit condition.
- "The brief is approved, so I can start while I write `TASK.md`."
- "They said the file is at X, so it's at X." Step 2 exists because that has
  been wrong before.

**Each of these means the brief is not ready. Go back to step 3.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Filling six fields from the prompt alone | The brief inherits the prompt's wrong premises and now looks approved |
| Briefing a two-line change | Overhead exceeds the work; a brief that is overhead stops being read |
| Presenting the brief inside `AskUserQuestion` | Six fields cannot be read in a dialogue box — print them first |
| Treating a blank Outputs as "decide later" | It is the signal to stop and go to `brainstormer`, not a gap to fill |

## Next step — you MUST take it

The brief is not the deliverable; the work is. When `TASK.md` is approved, say
which successor you are invoking and invoke it in the same turn: **straight to
the change** (the normal case — a brief concrete enough to approve is concrete
enough to build), or **`brainstormer`** when a blank field showed the approach is
still open.

**Never `writing-plans`.** It consumes an approved spec and six lines is not one
— its own description refuses a brief by name, and `workflow.md`'s Consumes
column says the same. Work that turns out to need real sequencing means the
brief was too big: say so and go to `brainstormer`, which produces the spec
`writing-plans` requires.

Stopping here is the chain's most common break: nothing watches for a finished
brief, so an un-handed-off brief is simply forgotten.

## Routing

- Mandatory validator: none. The approval gate in step 5 is the gate.
- Terminal handoff, and you MUST take it once the brief is approved — one of
  **two**, decided by what the brief says:
  1. The six fields are filled → do the change, then `verifying-work`.
  2. A field could not be filled because the approach is undecided → invoke
     `brainstormer`.
  Name which one you are taking. Stopping after writing `TASK.md` leaves the
  chain broken — nothing else will pick it up.
- **`writing-plans` is not among them**, and this listed it as a third branch
  until 2026-08-03 while step 6, `writing-plans`' own description and
  `workflow.md`'s Consumes column all said the opposite. Stage 3 takes an
  approved spec; sequencing work reaches it through `brainstormer`, never
  directly from here.
- **Alternative to `brainstormer`, never a predecessor.** Brainstormer exists
  because the first idea becomes an anchor; a finished brief *is* that anchor,
  since Goal and Outputs commit to a solution shape.
- The bailout is step 3's blank-field rule, not a handoff: if Outputs or
  Done-check can't be filled because the approach is undecided, abandon the
  brief and start at `brainstormer`. Don't guess fields to keep it alive.

## Success

`TASK.md` holds six approved fields, every inferred field was named at the
approval gate, and the Done-check is something a fresh session could run without
asking a question.
