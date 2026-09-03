# Knowledge doc formats

The per-file specification for the seven docs `knowledge-manager` owns. Load
this only for the file(s) actually being written — `SKILL.md`'s routing table
says which section applies.

## README.md

Stable project truth for a new human or agent: purpose, setup, usage,
architecture, repository map, conventions, and links to deeper docs. Do not put
active work, handoff state, historical entries, or capability-layer contracts
here. Update only when the project itself changes.

## TASK.md

A capped live ledger — the `<=6` most recent tasks, newest first, nothing
else. **Not** an accountability archive: an evicted task's record lives in
`LOG.md` (the line written when it finished), its `docs/plans/` doc, and
git history.

```
# Tasks
<!-- session-context:start -->
<!-- Live window: <=6 tasks, newest first. Evicted tasks live on in LOG.md + docs/plans/. -->

| Task | Status | Updated |
|---|---|---|
| <task name> ([plan](docs/plans/<date>-<slug>.md)) | Active | YYYY-MM-DD |
| <task name> (PR #NN) | Done | YYYY-MM-DD |
<!-- session-context:end -->
```

- **The `<!-- session-context:start -->` … `<!-- session-context:end -->`
  region is what `session-init/02-session-context.py` injects verbatim at
  every session start.** All of the file's live content sits inside it;
  keep it to six one-row entries so it is read whole, never clipped.
- **`Status`** is exactly one of `Active` · `Blocked` · `Done` — no
  synonyms.
- **`Updated`** is the date of the last logged subtask or status change.
- **`Task`** names the work and links its plan (`docs/plans/`) or its PR.
  The full Goal / Constraints / Done Checks / Out of Scope live in that
  plan doc and are never restated here — a task with no plan and no clear
  outcome isn't ready to execute, which is a signal for `task-analysis`
  to scope it rather than guess.
- **Eviction:** when a 7th task lands, drop the oldest `Done` row. Never
  drop a row still `Active` or `Blocked`. There is no ongoing `## Completed`
  section; the ~400-line archive this file used to carry was cut once to
  `docs/archive/task-log-pre-2026-09.md`.

## MEMORY.md

Long-term project conventions only — the things a new engineer or a fresh
session would otherwise have to rediscover by reading half the codebase.
Not a running log (that's `LOG.md`), not a snapshot of current work
(that's `HANDOFF.md`). If it wouldn't still be true in three months,
it doesn't belong here.

(Distinct from Claude Code's own auto-memory index under
`~/.claude/projects/<slug>/memory/` — same filename, different file,
different purpose: that one is about the user across all their projects,
this one is about the current project.)

## HANDOFF.md

A rewritten-in-place pickup note for the *current* work — not accumulated.
History is `LOG.md`; the task ledger is `TASK.md`. Overwrite it at the end
of any session that changed real state.

```
# Handoff
<!-- session-context:start -->
## Resume here
<one paragraph: what is true right now + the literal next action>

## Decisions (don't relitigate)
- <decision> — <why, one line>

## Blocked / needs a human
- <question + the options, if known>   (or: `nothing`)
<!-- session-context:end -->

## Ruled out
- <approach tried and abandoned> — <why, so it is not retried>
```

- **The `<!-- session-context:start -->` … `<!-- session-context:end -->`
  region is injected verbatim by `session-init/02-session-context.py` at
  every session start.** Only the three sections above sit inside it;
  `## Ruled out` and anything else stays below `:end`, read only on
  demand. Keep the marked region short — it is paid on every session.
- **Rewrite, don't append.** A HANDOFF.md that keeps every past handoff
  becomes a second `LOG.md` and the actually-current state gets buried
  under history.
- Point `Resume here` at the active `TASK.md` row rather than restating
  its detail.

## LOG.md

Running log, appended at the top, never rewritten. Each entry:

```
## YYYY-MM-DD HH:MM
<one to a few concise lines of what happened and why>
```

Get the actual current date/time rather than guessing. Very concise —
this is a log, not a report. **The newest entry is injected verbatim by
`session-init/02-session-context.py` at every session start** — a long
entry is paid on every session until it is superseded, so write the one
thing a future reader could not reconstruct from the diff and stop.

**Size:** the newest entry is ≤ ~15 lines (hard 20, enforced by
`tools/test_doc_entries.py`).

## ISSUES.md

Append-only, newest entry at the top (same discipline as `LOG.md`) — one entry per
*incident*, covering its whole diagnose/fix sequence, not one append per attempt.
**Each field is its own bullet, never a bare `Field: value` line** — consecutive
plain lines collapse into one run-on paragraph in standard Markdown; this holds
for every field-shaped block (this format and the decision records below):

```
## YYYY-MM-DD HH:MM — <short symptom title>
- **Phase/Context**:
- **Symptom**:
- **Diagnosis**:
- **Attempts**:
  - 1. <tried> → <fixed / still failing / partial>
- **Fix**:
- **Status**: `Resolved` | `Escalated` | `Abandoned`
```

Written by `systematic-debugging` once its four-phase loop reaches a terminal state.
Read on demand by grepping for a matching prior symptom, never cover to cover.

**Size:** each entry is ≤ ~12 lines (hard 16, enforced by
`tools/test_doc_entries.py`).

The **Attempts** field is the point of the entry, not padding: it records what was
tried and failed, which is what stops the next person re-running the same three
dead ends.

**Promotion rule to `MEMORY.md`**: after a `Resolved` entry, apply `MEMORY.md`'s own
durability question verbatim — "would this still be true in three months, independent
of this bug's code?" If yes, add one line to `MEMORY.md` referencing this entry by
date — never duplicate the Attempts detail there. `Escalated`/`Abandoned` incidents are
never promoted; an unresolved incident hasn't produced a proven lesson, only a
hypothesis.

## Decision records (`decisions/`)

One file per non-obvious, hard-to-reverse decision — not a restatement of
something already obvious from the code. Lightweight
ADR shape:

```
## Decision
## Why
## Alternatives considered
```

`decisions/README.md` explains the format once; individual decision files
don't repeat it.
