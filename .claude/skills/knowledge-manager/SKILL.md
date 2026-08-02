---
name: knowledge-manager
description: Use when a unit of work finishes and the repo's persistent docs no longer match reality, or when the staleness warning says LOG.md and HANDOFF.md are behind the work. Triggers include "log this", "update the docs", "record this", "write down what we decided", "note this for later", "handoff", "where did we get to", "capture this before we lose it", finishing a task, making a hard-to-reverse decision, or diagnosing a failure worth remembering. Owns TASK.md, PLAN.md, MEMORY.md, HANDOFF.md, LOG.md, ISSUES.md and decisions/. Do NOT use for CLAUDE.md, for a change with nothing worth recording, or to restate a diff that git already holds.
context:
  - formats.md
effort: high
model: opus
---

# Knowledge Manager

Owns exactly seven things: `TASK.md`, `PLAN.md`, `MEMORY.md`, `HANDOFF.md`,
`LOG.md`, `ISSUES.md`, `decisions/`. Nothing else. One hook warns about these
files and none can write them — a hook is a subprocess with no tool access, so
it can refuse a turn but cannot compose an entry. That is the gap this fills.

Cap visible output at ~500 tokens. The written entries are the deliverable; do
not also narrate them back.

## Gather evidence before you write

Do not write from memory. Memory is what produces a log entry that sounds right
and is wrong. Read the actual state first:

```bash
git status --porcelain          # what changed, including untracked
git diff --stat                 # size and shape of the change
git log --oneline -5            # what already landed
```

Take the commit SHA, the file count and the branch from that output, not from
recollection. Anything you claim was verified must have a command and its real
output behind it — if a suite was not run this turn, the entry says so.

## Never

- **Duplicate git history.** Git is the source of truth for what changed and
  when. These docs record engineering metadata — why, what's next, what was
  decided — not a second copy of the diff.
- **Store conversation history.** The decision, not the path to it.
- **Store temporary detail** that stops being true when the task ends.
- **Write "updated the docs" as the entry.** That is the one entry guaranteed
  to be worthless to the next reader.

A long file here means something that belonged in git history, or nowhere,
leaked in.

## Write for someone who was not here

The reader has none of your context, memory, or machine. `~/.claude` memory and
`claude --resume` are personal and machine-local; they do not reach a teammate,
a CI agent, or another workstation. These files are the only thing that does —
which is the entire reason they are committed rather than cached.

`session-start/02-bootstrap-docs.py` re-injects `HANDOFF.md`'s
`<!-- session-context -->` block and the last `LOG.md` entries at session start —
it was registered on 2026-08-02, having sat on disk unwired since 2026-08-01.
So the next session sees what you write here, but a teammate or a CI agent only
sees the file. Write for the one who opened it deliberately and knows nothing
else.

## Route first, then read one format section

Read only the section of [`formats.md`](formats.md) for the file you are
actually writing. Loading all seven specs to append one `LOG.md` line is the
waste this table exists to prevent.

| Write here | When | Update style |
|---|---|---|
| `TASK.md` | a task starts, changes status, or reaches Done | `## Active` in place; `## Completed` append-only |
| `PLAN.md` | a task needs an implementation plan | overwrite in place |
| `MEMORY.md` | a convention emerges that outlives the task | append, sparingly |
| `HANDOFF.md` | a session changed real state | overwrite in place |
| `LOG.md` | something happened worth a dated line | append at top |
| `ISSUES.md` | a diagnose-fix loop reached a terminal state (`systematic-debugging` writes these) | append at top, one entry per incident |
| `decisions/` | a non-obvious, hard-to-reverse choice was made | one new file |

Two rules cut across every format and are easy to get wrong:

- **Every field-shaped block uses bullets, never bare `Field: value` lines.**
  Consecutive plain lines collapse into one paragraph when rendered.
- **Keep `HANDOFF.md`'s `<!-- session-context -->` markers.** Inert today, but
  they define the boundary a re-registered bootstrap hook would pay for.

## What earns an entry

Record the thing a future reader could not reconstruct from the diff:

- A decision and the option it beat.
- A failure and what it actually was — especially where the symptom misled.
- A constraint discovered the hard way.
- Something asserted by prose that the wiring does not implement.
- What was verified, with the command, and what was not.

Skip: a rename, a typo fix, formatting, anything whose entire content is
visible in `git show`.

## Red Flags — the entry is not worth writing yet

- "Updated the skills and fixed some bugs." Which skills, which bugs, and what
  was wrong with them?
- Naming a file with no line and no symptom.
- "All tests pass" with no command and no output line.
- Writing `HANDOFF.md` as a second `LOG.md`. Handoff is state; log is history.
- Recording a decision without the alternative it beat — that is an assertion,
  not a decision record.
- Copying the diff into `LOG.md`.

**Each of these means: go back and read the actual state first.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Writing the entry from memory instead of `git status` | Produces a plausible entry that is wrong, which is worse than none |
| Appending to `HANDOFF.md` instead of overwriting | It becomes history, duplicates `LOG.md`, and the real current state gets buried |
| Rewriting an old `LOG.md` entry | Append-only; a corrected log is not a log |
| Claiming a check passed that was not run this turn | The one rule in CLAUDE.md with no automated guard |
| Filing every incident under `MEMORY.md` | Only promote a `Resolved` one that survives "still true in three months?" |

## Routing

- Mandatory validator: none. The gates that fire when these files go stale are
  `pre-run/04-docs-staleness.py`, which warns and nothing more.
  `post-run/05-docs-gate.py` (blocked the turn) and
  `pre-commit/05-docs-required.py` (denied the commit) were deleted on
  2026-08-02 — so recording is now entirely on you.
- Terminal handoff: none. This records and stops.
- Invoked at the end of a unit of work, not at the end of a session — a session
  that ran four units owes four log entries, written as each finished.
- Work that turns out to need doing, rather than recording, becomes its own task
  via `task-brief`. Do not absorb it here.

## Success

A reader with no context can tell, from the files alone, what changed, why,
what was proven, what was not, and what to do next — without opening the diff
and without asking a question.
