# Knowledge-doc head contract: bounded session-start reads, capped TASK.md ledger

**Source brief:** User request, 2026-09-01 — "harnesses should never read
entire LOG / TASK / other .md files; read only the top-most section,
separated by clear separators. TASK.md keeps a log of ~6 briefs with a
finished/unfinished status and a last-subtask timestamp — that's all.
HANDOFF.md is the active/finished task tracker. All .md files crisply
written to a preferred schema." Two forks resolved by the user:
task-history eviction is "your judgement / best practice"; the
TASK↔HANDOFF split is "ledger vs pickup-note".

**Goal:** Give every knowledge doc a fixed schema whose top region is an
explicitly delimited "head" the SessionStart hook reads *verbatim and in
full*, never a mid-word clip of a whole file. Redefine TASK.md as a
≤6-row status ledger and HANDOFF.md as a rewritten-in-place pickup note.

**Constraints:** `.claude/` stays the only source of truth; no new file
the hook reads lazily; the hook keeps its detect-drift classification and
authors no strategic content; `--tier all --require-test` green; the
change is coherent across `formats.md`, the hook, its contract tests,
`CLAUDE.md`, and `documentation/SKILL.md` in one branch.

**Input:** `.claude/hooks/session-init/02-session-context.py`,
`.claude/skills/documentation/{SKILL.md,formats.md}`,
`tools/claude_session_start_contract.py`,
`tools/test_session_start_contract.py`, `tools/test_doc_entries.py`,
`tools/test_hook_policy.py`, `CLAUDE.md`, `templates/project_docs.md`,
the live `TASK.md` (13 Active entries, ~400-line Completed archive) and
`HANDOFF.md` (305 lines of accreted Pending items).

**Output:** a decision record; rewritten `formats.md` TASK/HANDOFF
sections; a simplified hook (`parse_task_head`, `_emit_head`, no
mid-word `_clip` on injection paths); updated contract tests + a new
TASK.md head check; a re-pointed `CLAUDE.md` Knowledge-docs section;
`documentation/SKILL.md` corrections; migrated `TASK.md`/`HANDOFF.md`
plus a one-time `docs/archive/task-log-pre-2026-09.md` cut.

**Done Checks:** `python tools/run_checks.py --scoped` then
`python tools/run_checks.py --tier all --require-test` both exit 0;
`python .claude/hooks/session-init/02-session-context.py <<< '{}'` exits 0,
injects only the marked head regions, and `git status` shows it wrote
nothing; the two new contract-test cases (region-bounded read, newline-only
clip) pass and were proven red first.

**Out of Scope:** MEMORY.md / README.md / ISSUES.md schema changes (fine
as-is); `resume.py`'s `BRANCH_PREFIX` bug and the other pre-existing
HANDOFF pending items (preserved in the migration, not fixed here);
re-litigating non-hot-path doc content.

---

## Design

**One rule for the session-start hot path:** the hook reads only the region
between `<!-- session-context:start -->` and `<!-- session-context:end -->`,
emitted verbatim. A backstop ceiling clips only at a `\n` with a
`[Read <file> for the rest]` pointer; well-formed heads fit under it.

### TASK.md — capped live ledger

```
# Tasks
<!-- session-context:start -->
<!-- Live window: <=6 tasks, newest first. Evicted tasks live on in LOG.md + docs/plans/. -->

| Task | Status | Updated |
|---|---|---|
| Knowledge-doc head contract ([plan](docs/plans/2026-09-01-knowledge-doc-head-contract.md)) | Active | 2026-09-01 |
| SessionStart hook rename (merged 8b0bb85) | Done | 2026-09-01 |
| ... (<=6 rows) ... | | |
<!-- session-context:end -->
```

- Status vocab, terse: `Active` · `Blocked` · `Done` (replaces the
  7-stage `Requested → … → Done` chain).
- `Updated` = date of the last logged subtask / status change.
- Full brief detail (Goal / Constraints / Done Checks / Out of Scope)
  lives only in `docs/plans/<date>-<slug>.md`. TASK.md points, never
  restates.
- Eviction: a 7th task in drops the oldest `Done` row. Its record
  persists as the LOG.md line written when it finished, its plan doc, and
  git. No dedicated append-only archive going forward — the existing
  ~400-line Completed block is cut once to `docs/archive/`.

### HANDOFF.md — rewritten-in-place pickup note

```
# Handoff
<!-- session-context:start -->
## Resume here
<one paragraph: what's true now + the literal next action>
## Decisions (don't relitigate)
- <decision> - <why, one line>
## Blocked / needs a human
- <question + options>   (or "nothing")
<!-- session-context:end -->

## Ruled out
- <approach abandoned> - <why>
```

Only the three marked sections inject. "Ruled out" and anything else sit
below `:end`.

### LOG.md

Format unchanged. Hook keeps injecting the single newest entry, now whole
(not 500-char clipped), with the line-boundary backstop. `test_doc_entries.py`
already caps a new entry at 20 lines, so the backstop is belt-and-braces.

### Not injected, unchanged

MEMORY.md, README.md, ISSUES.md — schemas in `formats.md` already fine.

---

## Tasks

Sequential, single owner — the `Dependencies` chain is linear on purpose;
this is not a parallel-schedulable plan.

### Task 1: Decision record

- **Files:** `decisions/2026-09-01-knowledge-doc-head-contract.md`
- **Dependencies:** none
- Record the head-region read contract + capped ledger. Beat: whole-file
  clipping (mid-word cuts, unbounded active list); a lazily-read archive
  file (junk drawer nothing reads). Links
  `[[2026-08-31-knowledge-skills-consulted-not-staged]]`.
- **Check:** file exists with `## Decision` / `## Why` / `## Alternatives
  considered`.

### Task 2: Rewrite the schemas in formats.md

- **Files:** `.claude/skills/documentation/formats.md`
- **Dependencies:** Task 1
- Rewrite `## TASK.md` + `## HANDOFF.md`: new schemas, the marker region as
  the hook boundary for both, terse Status vocab (`Active`/`Blocked`/`Done`),
  eviction-to-LOG rule. Delete the stale "injection is off / nothing reads
  this file automatically" paragraph.
- **Check:** `grep` shows the new `session-context` region in both schema
  blocks and no "nothing reads this file automatically".

### Task 3: Rewrite the hook

- **Files:** `.claude/hooks/session-init/02-session-context.py`
- **Dependencies:** Task 2
- `parse_active_task_pointers` → `parse_task_head` (emit marked region
  verbatim). `parse_handoff_head`: marked region + `## Resume here` /
  `## Current Work` fallback for un-migrated installs; drop mid-word
  `_clip`. New `_emit_head(text, ceiling, file)` — newline-only clip +
  pointer. LOG = newest entry, whole. Update printed section headers.
  Missing-doc / env / stub / decisions reporting untouched.
- **Check:** `python .claude/hooks/session-init/02-session-context.py <<<
  '{}'` exits 0 and injects the marked heads only.

### Task 4: Update the session-start contract tests

- **Files:** `tools/test_session_start_contract.py`, `tools/claude_session_start_contract.py`
- **Dependencies:** Task 3
- Update assertions to the new parser; add "reads only the marked region"
  (row past `:end` not injected) and "no mid-line clip" (over-ceiling head
  cut on `\n`), each proven red first. Confirm `tools/test_hook_policy.py`
  still green.
- **Check:** `python tools/test_session_start_contract.py` exits 0;
  seeded-violation runs go red.

### Task 5: Add the TASK.md head check

- **Files:** `tools/test_doc_entries.py`
- **Dependencies:** Task 2
- Fix stale `knowledge-manager` → `documentation` in the docstring; add a
  TASK.md check — head carries `<!-- session-context:end -->` and ≤6 table
  rows (soft when the markers are absent, for un-migrated installs).
- **Check:** `python tools/test_doc_entries.py` exits 0; a 7-row fixture
  fails.

### Task 6: Re-point the CLAUDE.md Knowledge-docs section

- **Files:** `CLAUDE.md`
- **Dependencies:** Task 2
- One line each for the new TASK/HANDOFF roles; pointer to `formats.md` and
  the decision record; fix the stale `knowledge-manager` owner reference.
  Stays bootloader-terse.
- **Check:** `python tools/test_harness_contract.py` still green.

### Task 7: Correct documentation/SKILL.md

- **Files:** `.claude/skills/documentation/SKILL.md`
- **Dependencies:** Tasks 2, 3
- Routing-table TASK.md row; fix "markers inert today" (live now); fix the
  two passages describing what the hook injects.
- **Check:** `python tools/new_skill_check.py --all` and
  `python tools/test_process_router.py` exit 0.

### Task 8: Migrate the live docs

- **Files:** `TASK.md`, `HANDOFF.md`, `docs/archive/task-log-pre-2026-09.md`, `docs/archive/ARCHIVE.md`
- **Dependencies:** Tasks 2, 3
- TASK.md 13 Active + ~400-line Completed → 6-row table + one-time archive
  cut (pointer left behind; `ARCHIVE.md` acknowledges it). HANDOFF.md 305
  lines → new head + `## Known open items` + `## Ruled out`; every
  still-live pending item (ISSUES `0x08` bytes, `resume.py` `BRANCH_PREFIX`,
  "five state reporters", Gate 2 never fired) preserved, none dropped.
- **Check:** the hook injects a ≤6-row TASK head and the 3 HANDOFF
  sections, nothing below `:end`.

### Task 9: Verify and record

- **Files:** `LOG.md`
- **Dependencies:** Tasks 1–8
- `python tools/run_checks.py --tier all --require-test` exits 0; run the
  hook with `{}`, show exit 0 + injected block + `git status` proof it
  authored nothing; `documentation` writes the `LOG.md` entry.
- **Check:** `PASS: N check(s) green`; `test_doc_entries.py` passes on the
  new LOG entry.

## Context

`formats.md` and reality had already drifted: it mandates an append-only
TASK.md `## Completed` trail "answerable from day one" (exactly what the
user's "just 6 briefs" removes) and claims the SessionStart injection is
*off* ("nothing reads this file automatically") when the hook is wired in
`settings.json` and parses HANDOFF's `session-context` markers every
session. This plan makes the spec match a deliberately chosen behavior
rather than patching around the drift.
