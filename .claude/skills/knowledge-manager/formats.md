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

Two sections, two different rules — this file is the accountability trail
for every task in the repo's life, not just a scratchpad for the current one.

**`## Active`** — task(s) currently in progress. Overwrite in place as they
change; this part is current state, not a log. Each task is exactly:

```
## <task name>
- **Goal**:
- **Input**:
- **Output**:
- **Constraints**:
- **Done Checks**:
- **Out of Scope**:
- **Status**:
```

**Each field is its own bullet, never a bare `Field: value` line.** A single
newline between plain lines collapses into one run-on paragraph in
standard Markdown rendering (no blank line = no break) — bullets are the
only formatting that reliably renders each field on its own line across
renderers, without relying on trailing-space hard-break tricks. This
applies to every field-shaped block in this file (`TASK.md`'s two
formats, decision records) — anywhere a fixed set of labeled
fields gets written, use bullets, not consecutive plain lines. If any
single field's content itself needs sub-structure (e.g. `Input` listing
several files), nest a sub-bullet list under that field rather than
cramming it into one line.

A task without a clear Goal or Done Checks isn't ready to execute; that's a
confidence-gate signal for `workflow-orchestrator` to ask rather than guess.

Standard `Status` vocabulary — use these, don't invent synonyms: `Requested`
→ `Planning` → `Ready` → `Executing` → `Review` → `Validated` → `Done`.

**`## Completed`** — append-only, newest entry at the top (same discipline
as `LOG.md`). The moment a task's Status reaches `Done`, move it out of
`## Active` and append a compact record here — never delete a task outright,
and never rewrite a past entry. This is what makes the repo's history
answerable from day one: "what was asked, what shipped, when." Compact
shape per entry:

```
### YYYY-MM-DD — <task name>
- **Goal**:
- **Output**:
- **Status**: Done
```

(`Input`/`Constraints`/`Out of Scope` aren't repeated in the archive — git
history and the original commit/PR already carry that detail; the archive
entry only needs enough to answer what was asked and what shipped.)
`workflow-orchestrator`'s Knowledge Update stage is what performs this move.

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

Current-state snapshot: `Completed`, `Current Work` (one line, pointing at
the active task in `TASK.md` — don't duplicate its full detail here),
`Pending`, `Next Steps`, `Open Questions`. Overwritten in place every time —
status, not history (history lives in `LOG.md` and `TASK.md`'s `Completed`
section). Update at the end of any work session that changed real state.

**`<!-- session-context:start -->` / `<!-- session-context:end -->`** wrap
everything from `Current Work` through `Open Questions` (`Completed` stays
outside, above the markers).

These are currently inert. `session-start/02-bootstrap-docs.py` used to inject
what sits between them at every `SessionStart`. It has been unregistered before
for force-feeding ~20,000 bytes into every session, which
made a fresh session impossible. The script is still on disk and can be
re-registered, so keep the markers and keep honouring the boundary — anything
inside is what a future re-registration would pay for on every session start.

**With the injection off, nothing reads this file automatically.** It is now
purely a cross-boundary document: written for a teammate, a CI agent, another
machine, or a session that has to open it deliberately. Write it for a reader
with none of your context.

## LOG.md

Running log, appended at the top, never rewritten. Each entry:

```
## YYYY-MM-DD HH:MM
<one to a few concise lines of what happened and why>
```

Get the actual current date/time rather than guessing. Very concise —
this is a log, not a report.

## ISSUES.md

Append-only, newest entry at the top (same discipline as `LOG.md`) — one entry per
*incident*, covering its whole diagnose/fix sequence, not one append per attempt:

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
