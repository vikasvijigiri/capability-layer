---
name: knowledge-manager
model: opus
description: Owns the format and upkeep of a repo's persistent engineering docs — TASK.md, PLAN.md, MEMORY.md, HANDOFF.md, LOG.md, ISSUES.md, decision records. Use for "update the docs", "handoff", "log this", "record this decision", "write down what we decided", "note this for later", "where did we get to", when starting or finishing a unit of work, when a design decision is made or a failure diagnosed, and when those files no longer match reality. Prefer this over editing them freehand — a stale HANDOFF is worse than none, because the next session trusts it. Do NOT use for CLAUDE.md — repo-onboarding owns that.
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
provides: [knowledge-update]
requires: []
produces_artifact: true
retryable: true
---

# Knowledge Manager

Maintains exactly seven things, and nothing else: `TASK.md`, `PLAN.md`,
`MEMORY.md`, `HANDOFF.md`, `LOG.md`, `ISSUES.md`, decision records. All are
created as empty skeletons by the Repository Bootstrap hook the first time
a repo is opened — this skill defines what goes *inside* them once there's
real content.

## Never

- Duplicate git history — git itself is the source of truth for what
  changed and when; these docs record *engineering metadata* (why, what's
  next, what was decided), not a second copy of the diff.
- Store conversation history — no transcript of how a decision was
  reached, only the decision itself.
- Store temporary implementation details — scratch notes, half-finished
  reasoning, anything that stops being true the moment the task ends.

Keep every file concise. A long file here is a sign something that
belongs in git history or nowhere leaked in.

## Which file, and where its format lives

Route first, then read only that doc's section of
[`formats.md`](formats.md) (alongside this file, same folder) — not the whole
spec. Most invocations touch one
or two docs; loading all seven formats to append a `LOG.md` line is exactly
the waste `engineering-policy`'s context-economy principle names.

| Write here | When | Update style |
|---|---|---|
| `TASK.md` | a task starts, changes status, or reaches `Done` | `## Active` in place; `## Completed` append-only |
| `PLAN.md` | a task needs an implementation plan | overwrite in place |
| `MEMORY.md` | a convention emerges that outlives the task | append, sparingly |
| `HANDOFF.md` | any session that changed real state ends | overwrite in place |
| `LOG.md` | something happened worth a dated line | append at top |
| `ISSUES.md` | `error-recovery` reaches a terminal state | append at top, one entry per incident |
| `decisions/` | a non-obvious, hard-to-reverse choice is made | one new file |

Two rules cut across the formats and are easy to get wrong, so they are
stated once here as well as in the spec: **every field-shaped block uses
bullets, never bare `Field: value` lines** (consecutive plain lines collapse
into one paragraph when rendered), and **`HANDOFF.md`'s
`<!-- session-context -->` markers are load-bearing** — the bootstrap hook
injects only what sits between them at every `SessionStart`, so never
remove them and never park non-live content inside them.
