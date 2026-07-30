# Knowledge doc formats

The per-file specification for the seven docs `knowledge-manager` owns. Load
this only for the file(s) actually being written — `SKILL.md`'s routing table
says which section applies.

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
formats, `PLAN.md`, decision records) — anywhere a fixed set of labeled
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

## PLAN.md

The active implementation plan, if the current task has one:

```
## Objective
## Execution Plan
## Dependencies
## Risks
## Acceptance Criteria
```

Overwrite in place. This is a persistent, checked-in doc — distinct from
Claude Code's own ephemeral plan-mode file under `~/.claude/plans/`, which
is a per-session scratch artifact for getting the user's approval and
isn't checked into the repo.

### Execution Plan — one row per step, dispatch declared

`## Execution Plan` is a table, not prose. Every step names **who executes it**
before execution starts, so the dispatch choice is reviewable up front and
auditable afterwards instead of being decided silently in the moment:

```
| # | Step | Owner | Kind | Depends on |
|---|------|-------|------|-----------|
| 1 | Draft the PRD | requirements-analyst | skill | — |
| 2 | Pick stack + write ADR | stack-selector | skill | 1 |
| 3 | Implement API | backend-engineer | subagent | 2 |
| 4 | Implement UI | frontend-engineer | subagent | 2 |
| 5 | Review the diff | code-review | skill | 3, 4 |
| 6 | Deploy | (resolve-at-runtime) | — | 5 |
```

- **Owner** — the exact skill, subagent, or workflow that runs the step. Use the
  real registered name (it must exist in the Skill Registry, the agent roster, or
  `workflows/`), never a description of one.
- **Kind** — `skill` · `subagent` · `workflow` · `direct`. `direct` means the main
  context does it inline with ordinary tools; use it rather than inventing an owner
  for a step too small to delegate.
- **Depends on** — step numbers only. Two steps with disjoint dependencies *and*
  disjoint files/APIs/schemas are the parallel-safe set; this column is what makes
  that judgment checkable instead of asserted.

**Hooks are never Owners.** They fire on events regardless of what any plan says, so
a plan cannot invoke one. If a hook backstops a step, mention it in the Step text
(e.g. "commit — `git-delivery-guard` will scan"), never in the Owner column.

**`(resolve-at-runtime)` is a legitimate entry**, for steps whose owner genuinely
can't be known until an earlier step produces output. Mark it explicitly. An honest
unknown is fine; a confidently wrong Owner is not.

**The tag binds execution.** Whoever executes the plan dispatches as tagged, or
states the deviation and why *before* acting on it — see `workflow-orchestrator`
§4. A plan whose Owners are quietly ignored is worse than one with no Owner column,
because it reads as a guarantee it isn't keeping.

## MEMORY.md

Long-term project conventions only — the things a new engineer or a fresh
session would otherwise have to rediscover by reading half the codebase.
Not a running log (that's `LOG.md`), not a snapshot of current work
(that's `HANDOFF.md`). If it wouldn't still be true in three months,
it doesn't belong here.

(Distinct from Claude Code's own auto-memory index under
`~/.claude/projects/<slug>/memory/` — same filename, different file,
different purpose: that one is about the user across all their projects,
this one is about this repo.)

## HANDOFF.md

Current-state snapshot: `Completed`, `Current Work` (one line, pointing at
the active task in `TASK.md` — don't duplicate its full detail here),
`Pending`, `Next Steps`, `Open Questions`. Overwritten in place every time —
status, not history (history lives in `LOG.md` and `TASK.md`'s `Completed`
section). Update at the end of any work session that changed real state.

**`<!-- session-context:start -->` / `<!-- session-context:end -->`** wrap
everything from `Current Work` through `Open Questions` (`Completed` stays
outside, above the markers). The Repository Bootstrap hook injects only
what's between these markers at `SessionStart` — not the whole file. This is
a hard boundary, not a heading-name heuristic: whatever gets added to this
file in the future, keep it outside the markers unless it's genuinely live
status, since anything inside gets paid for on every session start. Never
remove the markers when editing this file.

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

Written by `error-recovery` once a bounded diagnose-fix-reverify loop reaches a
terminal state. Not preloaded at `SessionStart` (unlike `LOG.md`'s last-5-entries
treatment) — same "filenames only, read on demand" handling `decisions/` already gets,
since it's consulted on-demand by `error-recovery` grepping for a matching prior
symptom, not read cover-to-cover every session.

**Promotion rule to `MEMORY.md`**: after a `Resolved` entry, apply `MEMORY.md`'s own
durability question verbatim — "would this still be true in three months, independent
of this bug's code?" If yes, add one line to `MEMORY.md` referencing this entry by
date — never duplicate the Attempts detail there. `Escalated`/`Abandoned` incidents are
never promoted; an unresolved incident hasn't produced a proven lesson, only a
hypothesis.

## Decision records (`decisions/`)

One file per non-obvious, hard-to-reverse decision — not a restatement of
something already obvious from the code or from `PLAN.md`. Lightweight
ADR shape:

```
## Decision
## Why
## Alternatives considered
```

`decisions/README.md` explains the format once; individual decision files
don't repeat it.
