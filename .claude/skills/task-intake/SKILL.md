---
name: task-intake
model: opus
description: Converts a rough, informal ask into a structured, confidence-scored brief and gets explicit approval before anything is logged or executed. Use for a new feature idea, a bug report, "can we support X", "add Y to the app", "I want users to be able to X", "users should be able to X", "it would be nice if", a vague architecture question, or anything where Goal/Input/Output/Constraints aren't spelled out. Prefer this over restating a brief inline — it is the only path that gets scope approved before work starts. Do NOT trigger for direct factual questions, one-word confirmations ("yes", "continue", "done"), or continuations of an already-approved brief.
effort: high
argument-hint: "[the rough ask, in your own words]"
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - AskUserQuestion
  - Skill
provides: [intent-capture, task-brief]
requires: [rough_prompt]
produces_artifact: false
retryable: true
---

# Task Intake

Turns "Can we support multiple speakers?" into a brief someone could act on without
re-reading the original chat — then stops and asks before anything is persisted or
built. This is a deliberately narrow skill: it does not write `TASK.md`, does not plan,
does not spawn agents. It produces one thing — an *approved* brief — and hands off.

## Why this is its own skill, not a hook

A hook fires once, mechanically, at prompt-submission time — it can inject a reminder,
but it cannot hold a multi-step "restate → ask → wait for approval → refine → approval"
loop across a turn. That's a stateful, judgment-heavy workflow, which is exactly what a
skill is for. `task-brief-nudge` (the `UserPromptSubmit` hook) only nudges toward
invoking this skill; it does not — and structurally cannot — carry out the loop itself.

## When to use

Any new, non-trivial engineering ask that hasn't already been broken down — a feature
request, a bug report worth tracking, a real architecture question. Reuse the same
triviality bar `task-brief-nudge` already uses: skip entirely for trivial asks, direct
factual questions, or messages that are answers/continuations rather than new tasks
(the hook's own wordlist of confirmations — "yes", "continue", "done", etc. — never
reaches this skill in the first place).

## Steps

1. **Extract the brief** from the rough prompt, mapped directly onto
   `knowledge-manager`'s `TASK.md` field names — no separate vocabulary to translate
   later:
   - **Goal** — what "done" looks like, in one or two sentences.
   - **Input** — what's given/available to work from.
   - **Output** — the concrete artifact or change expected.
   - **Constraints** — anything explicitly stated as a boundary (tech, scope, style).
   - **Done Checks** — how anyone (including a future session) could verify this
     actually shipped.
   - **Out of Scope** — anything adjacent that should explicitly NOT happen, so it's
     never smuggled in silently later.
   Only fill a field from what was actually said or is directly inferable from the repo
   — an unstated field stays genuinely blank rather than guessed, matching this
   project's own "no placeholders, ask instead" convention.

2. **Score confidence** (0-100%) — how completely the six fields above could be filled
   without guessing. This is a judgment call, not a formula: weight it down for missing
   Constraints/Out-of-Scope (the two fields most often silently assumed), weight it down
   further if Done Checks can't be stated concretely.
   - **≥75%**: go straight to step 3 with the brief as drafted.
   - **<75%**: ask targeted clarifying questions first (`AskUserQuestion`, one round,
     focused only on the specific missing/ambiguous fields — not a generic "tell me
     more") — then redraft the brief before presenting it.

3. **Present the brief, then gate it with a real dialogue.** Write out all six fields
   plus the confidence score as plain text first — the brief has to be readable before
   it can be judged, and a dialogue box is not a place to read six fields. Then call
   `AskUserQuestion` with these three options, in this order:

   - **Approve** — say explicitly what approving commits to, naming any field filled by
     assumption rather than by what the user actually said.
   - **Keep refining** — nothing is written; redraft from the correction and present
     again. This is the loop, and it may run more than once.
   - **Cancel** — no brief, no plan, nothing written, `TASK.md` untouched.

   `AskUserQuestion` always appends **Other** with free-text input, which is how the
   user adjusts one specific field rather than picking a whole outcome. That is why a
   fixed list is safe here; an earlier version of this step forbade multiple choice for
   exactly that concern, and the free-text escape answers it.

   Fold the highest-impact unknowns into the *same* dialogue as additional questions
   (max four total) rather than resolving them in a later round — the fields that would
   otherwise send you straight back into "keep refining" are the ones worth asking about
   while the dialogue is already open.

   Treat a plain affirmative in chat as approval too; the dialogue is the default path,
   not a hoop to force someone through if they have already said yes. Anything that is
   not approval is feedback — incorporate it and re-present.
   **Nothing gets written anywhere until this step produces an explicit approval.**

4. **Hand off, don't execute.** Once approved:
   - Invoke `knowledge-manager` to persist the approved brief into `TASK.md` in the
     exact format its `formats.md` defines (Goal/Input/Output/Constraints/Done-checks/
     Out-of-scope, `Status: In Progress`).
   - If the work is genuinely multi-step, this is also the point to engage
     `workflow-orchestrator` for the actual planning/execution phase — that phase reads
     the approved brief as its starting input, it doesn't re-derive it.
   - This skill's own responsibility ends the moment the brief is approved and hand off
     is issued — it does not plan, implement, or verify anything itself.

## Relationship to other skills

- **`requirements-analyst`** is the heavier sibling — full PRD, MVP-cut feature list,
  acceptance criteria per feature, built for `mvp-builder`'s autonomous pipeline. This
  skill is the lightweight version for a single conversational ask, not a full product
  scope. If a rough ask turns out to actually need a full PRD (multiple features, real
  scope-cut decisions), say so and suggest `requirements-analyst` instead of forcing it
  into a single six-field brief.
- **`knowledge-manager`** owns the actual `TASK.md` write — this skill only ever hands
  it an already-approved brief, never writes the file itself.
- **`workflow-orchestrator`** owns what happens after approval for multi-step work —
  this skill's brief is its input, not a replacement for its own planning step.

## Note on project-local overrides

A repo can have its own `.claude/skills/task-intake/` with a repo-tailored version
(e.g. extra required fields for a regulated domain, or a different confidence
threshold). Where both exist, the project-local one takes precedence for that repo —
this global version is the default for any repo that doesn't have its own.
