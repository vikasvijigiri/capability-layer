## Decision

The SessionStart context hook (`.claude/hooks/session-init/02-session-context.py`)
reads a bounded, explicitly delimited **head region** of each knowledge
doc and emits it verbatim — never a character-count clip of a whole file.
The region is `<!-- session-context:start -->` … `<!-- session-context:end -->`
for `TASK.md` and `HANDOFF.md`; for `LOG.md` it is the single newest dated
entry. A backstop ceiling may only cut at a newline, with a
`[Read <file> for the rest]` pointer appended.

`TASK.md` is redefined as a **capped live ledger**: a `<=6`-row table of
`| Task | Status | Updated |`, newest first, Status one of
`Active` · `Blocked` · `Done`. Full brief detail lives only in
`docs/plans/<date>-<slug>.md`. When a 7th task lands, the oldest `Done`
row is evicted; its record persists as the `LOG.md` line written when it
finished, its plan doc, and git history. There is no ongoing append-only
`## Completed` section.

`HANDOFF.md` is redefined as a **rewritten-in-place pickup note**: three
marked sections (`## Resume here`, `## Decisions`, `## Blocked / needs a
human`) inside the region, `## Ruled out` and anything else below it.

## Why

**A bounded region beats a character clip.** The prior hook clipped
`HANDOFF.md` to 1000 chars and `LOG.md` to 500, mid-word, appending a
`[... clipped]` marker — so every session opened on a truncated sentence,
and the "active task pointers" parser dumped one line per entry in a
`## Active` list that had grown to 13 (most already finished). The head
region moves the size discipline into the file's *schema*: the author
writes a head that fits, the hook reads all of it, and a reader never
sees half a word. The delimiter also makes "what the session pays for on
every start" a visible, greppable thing in the file rather than a number
buried in the hook.

**A capped ledger beats an append-only trail for this file.** `formats.md`
had required `TASK.md` keep a `## Completed` section "answerable from day
one," which is why the live file carried ~400 lines nothing reads at
session start. The accountability that section provided is already
covered three times over — `LOG.md` (the append-only receipt, one line
per finished unit), `docs/plans/` (the full brief and its outcome), and
git. Keeping a fourth copy in the one file the hook reads every session
is pure recurring cost. The existing ~400-line block is cut once to
`docs/archive/`, not carried.

**`formats.md` matched neither the user's ask nor reality.** It also
claimed the injection was off ("nothing reads this file automatically")
while the hook was wired in `settings.json` and parsing the
`session-context` markers every session. This decision makes the spec
describe a deliberately chosen behavior instead of a drifted one.

See `[[2026-08-31-knowledge-skills-consulted-not-staged]]` for the
adjacent decision that domain-knowledge docs are consulted, not staged —
same instinct: one owner, read on demand, not force-fed every turn.

## Alternatives considered

- **Keep clipping whole files, just raise the budgets.** Rejected: the
  failure mode is mid-word truncation and an unbounded `## Active` list,
  not the budget size. A bigger budget delays both, fixes neither, and
  costs more per session.
- **A dedicated `docs/tasks-archive.md` read lazily.** Rejected: it is a
  new file nothing on the hot path reads, i.e. a junk drawer — the same
  anti-pattern `templates/project_docs.md` warns about for `HANDOFF.md`
  ("a LOG.md with extra steps"). `LOG.md` + `docs/plans/` + git already
  answer "what was asked, what shipped, when."
- **Keep a `## Completed` section in `TASK.md`, cap only `## Active`.**
  Rejected as the ongoing rule (still grows forever in the file the hook
  reads), but used *once* for the existing backlog: the ~400 lines move
  to `docs/archive/task-log-pre-2026-09.md` intact rather than being
  deleted.
- **A per-file first-`##`-section heuristic instead of an explicit
  marker.** Rejected: fragile against a future section reordering, and
  invisible — an explicit `<!-- session-context -->` pair is
  self-documenting about what the session pays for, and the hook already
  had the paired-marker parser for `HANDOFF.md`.
