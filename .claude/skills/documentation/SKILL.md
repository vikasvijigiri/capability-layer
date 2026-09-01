---
name: documentation
description: Update the durable project docs when they stop matching reality. Owns README, TASK, MEMORY, HANDOFF, LOG, ISSUES and decisions/, recording only what a future reader could not reconstruct from the diff. Triggers include "update the README", "update the docs", "log this", "record this", "note this decision", "write an ADR", "hand this over", or "catch me up". Do NOT use for CLAUDE.md or agent-layer contracts (capability-layer-maintenance), or to restate a diff. Use this whenever a unit of work ends, even if unasked.
effort: low
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Documentation

Owns exactly seven things: `README.md`, `TASK.md`, `MEMORY.md`, `HANDOFF.md`,
`LOG.md`, `ISSUES.md`, `decisions/`. Nothing else. **No hook watches these files
any more** — a hook is a subprocess with no tool access, so it could refuse a
turn but never compose an entry, and every hook that tried was deleted.
That is the gap this fills, and nothing now reminds you it is open.

Cap visible output at ~500 tokens. The written entries are the deliverable; do
not also narrate them back.

**Cap each written entry too.** A `LOG.md` entry is ~15 lines, a `HANDOFF.md`
section ~10, an `ISSUES.md` incident ~12. These files are re-read on every
session that loads them, so length is a recurring cost, not a one-off. Write the
one thing a future reader could not reconstruct from the diff and stop. If an
entry needs more, it is carrying detail that belongs in the diff, the plan, or
an ADR.

## The order

1. Gather evidence from the tree — `git log`, the diff, the checks that ran.
   Never write from memory of the conversation.
2. Decide which documents the change actually touches. Most units of work touch
   one or two, not all six.
3. Read the matching section of `formats.md` for each, and only that section.
4. Request the write permission, then write the entries, each anchored to
  something a reader can verify. `Write` is intentionally not pre-approved in
  this layer because these documents are durable repository state.
5. If this turn wrote to `LOG.md` or `ISSUES.md`, run `python
  tools/test_doc_entries.py` before moving on. It checks only the
  entry you just wrote (uncommitted, append-only), so a failure names
  your own new entry, not the backlog. Cut it to size or split it, then
  re-run, before calling the write done.
6. State which files you wrote and what you deliberately left unchanged.

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
- **Phrase an entry as a directive to a future reader.** `session-init/
  02-session-context.py` injects the `<!-- session-context -->` head of
  `TASK.md` and `HANDOFF.md` and `LOG.md`'s newest entry verbatim into every
  later session. Describe what happened; a line that reads as an instruction
  gets replayed as one, unreviewed.

A long file here means something that belonged in git history, or nowhere,
leaked in.

## Write for someone who was not here

The reader has none of your context, memory, or machine. `~/.claude` memory and
`claude --resume` are personal and machine-local; they do not reach a teammate,
a CI agent, or another workstation. These files are the only thing that does —
which is the entire reason they are committed rather than cached.

`session-init/02-session-context.py` injects the `<!-- session-context -->`
head of `TASK.md` and `HANDOFF.md`, plus `LOG.md`'s newest entry, at every
session start. So the next session sees what you write in those regions, but a
teammate or a CI agent only sees the file. Write for the one who opened it
deliberately and knows nothing else.

## Route first, then read one format section

Read only the section of [`formats.md`](formats.md) for the file you are
actually writing. Loading all seven specs to append one `LOG.md` line is the
waste this table exists to prevent.

| Write here | When | Update style |
|---|---|---|
| `TASK.md` | a task starts, changes status, or reaches Done | the ≤6-row ledger, in place; evict the oldest `Done` row |
| `README.md` | stable project purpose, setup, usage, architecture, or conventions change | update the relevant section; link deeper docs |
| `MEMORY.md` | a convention emerges that outlives the task | append, sparingly |
| `HANDOFF.md` | a session changed real state | overwrite in place |
| `LOG.md` | something happened worth a dated line | append at top |
| `ISSUES.md` | a diagnose-fix loop reached a terminal state (`debugging` writes these) | append at top, one entry per incident |
| `decisions/` | a non-obvious, hard-to-reverse choice was made | one new file |

**`README.md`'s install/setup commands are executable claims, not prose —
run them, don't proofread them.** A wrong URL, a stale org name, or a
missing flag reads fine and fails silently for the next person who copies
it. Found live: the install commands named an old GitHub org
(`NG-VikasV`, redirects but is not the canonical remote) and, more
seriously, omitted `--force-reinstall` — `pyproject.toml`'s static
`version = "0.1.0"` means a plain `pip install` (even with `--upgrade`)
sees "already satisfied" and silently keeps whatever was installed
before, no error, no warning (`decisions/` or `ISSUES.md` per the fix's
weight — this one was small enough for a direct `LOG.md`/`ISSUES.md`
entry, not a full ADR). When `README.md`'s install, setup, or verify
commands are the thing changing, actually run them — a fresh venv or a
scratch directory, the same evidence standard as any other check — before
writing the section that claims they work.

Two rules cut across every format and are easy to get wrong:

- **Every field-shaped block uses bullets, never bare `Field: value` lines.**
  Consecutive plain lines collapse into one paragraph when rendered.
- **Keep `TASK.md`'s and `HANDOFF.md`'s `<!-- session-context -->` markers.**
  They bound exactly what `02-session-context.py` injects on every session —
  keep the region small.

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
- "The install command in `README.md` looks right, I'll skip running it."
  It looked right the last time too, right up until it silently installed
  a stale package.
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

- Mandatory validator: `python tools/test_doc_entries.py`, when `LOG.md`
  or `ISSUES.md` was written this turn — see "The order" step 5. No hook
  runs it for you: `05-docs-gate.py` (blocked the turn), `05-docs-required.py`
  (denied the commit) and `04-docs-staleness.py` (warned each turn) were
  all deleted — the direction for this file family is pull, not push.
  The check itself already exists and is already registered
  against both files in `.claude/project-checks.json`'s `test_map`, so
  `tools/run_checks.py --scoped` also catches a violation later — this
  step is what catches it now, before it is committed.
- Terminal handoff: none. This records and stops.
- Invoked at the end of a unit of work, not at the end of a session — a session
  that ran four units owes four log entries, written as each finished.
- Work that turns out to need doing, rather than recording, becomes its own unit
  and enters the chain at `.claude/workflow.md` §Entry, which is one door:
  `task-analysis`. Do not absorb it here.

## Success

A reader with no context can tell, from the files alone, what changed, why,
what was proven, what was not, and what to do next — without opening the diff
and without asking a question.
