# Fix predicted-vs-actual execution-level comparison to use per-turn deltas Implementation Plan

## Approved

Gate 1 approved via `ExitPlanMode`, as part of a 5-item response to
"give me a proper plan to fix and make it world class." This is the one
of the five ready for immediate implementation; the other four (schema
coverage, a full objectives re-audit, the duplicate-call-rate
investigation, two stale doc cross-references) are each scoped as their
own follow-up, not part of this plan.

**Goal:** Make `09-telemetry.py`'s `execution_level.actual` a genuine
per-turn measurement (as `01-entry-classifier.py`'s
`execution_level.predicted` already is), instead of a session-cumulative
total compared against a per-turn forecast — the mismatch that produced
`predicted: E0, actual: E5` on an ordinary turn this session, making
objective 8/9/18/30's core self-check metric untrustworthy.

**Source brief:** this session's grounded-verdict pass over the 30
primary objectives (unrecorded as a doc; the finding and the fix
direction are stated here in full). `docs/objectives.md`'s own
instrument table (line 100) cites `execution_level.predicted`/`.actual`
as objective 8/9/18/30's evidence.

**Slug:** telemetry-per-turn-execution-level

**Risk:** high — forced by `control-surface`. Per `tools/scope.py --plan
docs/plans/2026-08-22-telemetry-per-turn-execution-level.md`: `risk:
high -- high forced by: control-surface` / `scope: major -- vetoed by:
control-surface, spread`. Not a judgment call — any `.claude/hooks/`
path is high regardless of diff size. Gate 2 is still owed.

**Blast radius:** `.claude/hooks/telemetry/09-telemetry.py` (the `Stop`
hook that writes every `telemetry.jsonl` row) and `tools/test_bench.py`
(its existing, real test coverage for this exact function). No other
hook reads `execution_level.actual`; `tools/bench.py`'s own report
prints `execution_level` fields only via `docs/research/*.md`-style
manual reads, not a second code path that would need updating.

**Rollback:** `git revert` the commit. `telemetry.jsonl` is
append-only and gitignored (per-machine state, `data-analysis/SKILL.md`);
a reverted hook simply resumes writing the old (buggy) cumulative
comparison on the next `Stop` — no migration, no schema change to the
file itself (same keys, same shapes, only which numbers feed them).

**Architecture:** `_actual_execution_level()` in `09-telemetry.py` is
already correctly unit-tested in `tools/test_bench.py:170-187` against
**synthetic per-turn-shaped inputs** (`_ael({"calls": 1}, {"calls": 1}, 5)`
— a single skill call, a single agent call, five tool calls). The
function itself is not the bug. The bug is in `build_snapshot()`
(same file, lines 234-310): it passes the **raw session-cumulative**
`skills_loaded`, `agent_totals`, and `tool_totals.get("calls", 0)`
dicts straight into that function — the exact shape its own tests
prove was never the intended input. `01-entry-classifier.py`'s
`execution_level_predicted`, by contrast, genuinely is a per-turn
forecast (computed fresh at each `UserPromptSubmit`). Comparing a
per-turn forecast against a session-cumulative "actual" means the
"actual" side can only ratchet toward `E5` as a session lengthens,
regardless of how small any single turn was — which is exactly the
`predicted: E0, actual: E5` mismatch observed this session (see
`.claude/hooks/state/telemetry.jsonl`'s last row before this fix).

The module's own docstring (lines 6-15) already anticipated this and
left the door open rather than closing it: *"this writes the full
cumulative-to-date snapshot every turn, append-only — a later reader
can diff two rows for a real per-turn delta if one is ever needed, so
this does not foreclose that."* This plan is that later reader. No new
mechanism, no schema change: `build_snapshot()` reads the previous
`telemetry.jsonl` row (if one exists), computes `current - previous`
for the three counters `_actual_execution_level()` already consumes,
clamps each to `>= 0` (a negative delta means the underlying state file
was reset between turns, e.g. `.claude/hooks/state/` cleared — not a
real negative count), and passes the **deltas** in. `run_scope` and
every other field's cumulative meaning are unchanged; only the three
inputs to this one function change from cumulative to delta.

**Tech stack and constraints:** Plain Python, no new dependency. Must
not change `telemetry.jsonl`'s on-disk schema (other tools/dashboards
may already parse it) — only the *value* of `execution_level.actual`
changes, never its key or type (`str | None`, same as today). Must not
slow down the `Stop` hook meaningfully: `telemetry.jsonl` is currently
276KB/130 lines and grows without bound (append-only, never truncated,
per its own docstring), so reading "the previous row" must be a bounded
tail-read (last few KB), never a full-file load that gets slower every
session as the file grows over a repo's lifetime.

## Grounding — existing patterns this plan follows

| Category | Pattern | Citation |
|---|---|---|
| `_actual_execution_level()`'s real input shape | Already unit-tested against per-turn-scale dicts, not cumulative ones | `tools/test_bench.py:170-187` |
| The fix was anticipated, not invented | "a later reader can diff two rows for a real per-turn delta... this does not foreclose that" | `.claude/hooks/telemetry/09-telemetry.py:6-15` |
| Reading a JSON state file defensively (missing/corrupt = empty, never raise) | `_load_json()`, already in this same file | `.claude/hooks/telemetry/09-telemetry.py:114-118` |
| A reporting hook must never fail the turn it reports on | `main()`'s top-level `try/except: pass` | `.claude/hooks/telemetry/09-telemetry.py:313-323` |
| Regression style: name the specific inversion a mapping bug produces, not just "returns a valid label" | The `>4 agents -> E5, not E4` comment explaining WHY that test exists | `tools/test_bench.py:163-169` |

`python tools/memory.py --paths .claude/hooks/telemetry/09-telemetry.py
tools/test_bench.py` returned only generic `.claude`-directory-level
hits (naming its directory, nothing specific to this function or this
delta question) — no prior attempt or caution to reconcile with.

## File map

- Modify: `.claude/hooks/telemetry/09-telemetry.py` — add a bounded
  previous-row reader and per-turn delta computation in
  `build_snapshot()`; `_actual_execution_level()` itself is unchanged
- Modify: `tools/test_bench.py` — new tests proving the delta
  computation, with a red-green check against the pre-fix behavior

## Progress

- [x] Task 1 — Read the previous telemetry row and compute per-turn deltas
- [x] Task 2 — Prove it with a red-green regression test

## Tasks

### Task 1: Read the previous telemetry row and compute per-turn deltas
**Purpose:** feed `_actual_execution_level()` the per-turn counts its
own tests already assume, instead of session-cumulative totals.
**Files:**
- Modify: `.claude/hooks/telemetry/09-telemetry.py:114-118` (add a
  `_tail_last_json_line()` helper near `_load_json()`)
- Modify: `.claude/hooks/telemetry/09-telemetry.py:234-310`
  (`build_snapshot()`: compute deltas before calling
  `_actual_execution_level()`)
**Dependencies:** none
**Implementation notes:** Add
`_tail_last_json_line(path: Path, max_bytes: int = 8192) -> dict`:
open `path` in binary mode, seek to `max(0, size - max_bytes)`, read to
end, decode, split on `\n`, drop the trailing empty element, take the
last non-empty line, `json.loads` it inside a `try/except (OSError,
ValueError): return {}` — matching `_load_json()`'s own defensive
shape one function up. In `build_snapshot()`, before building the
`skills_loaded`/`agent_totals`/`tool_totals` values that currently feed
`_actual_execution_level()` directly (lines ~279-280), call
`previous = _tail_last_json_line(TELEMETRY)` (the *existing* file,
before this turn's row is appended — `TELEMETRY` is only ever appended
to at the very end of `main()`, so at this point in `build_snapshot()`
it still holds only prior turns). Extract
`prev_skill_calls = (previous.get("skills_loaded") or {}).get("calls", 0)`,
`prev_agent_calls = (previous.get("agents_spawned") or {}).get("calls", 0)`,
`prev_tool_calls = (previous.get("api_calls") or {}).get("calls", 0)`
(defaulting to `0` when `previous` is `{}`, i.e. first turn — matching
"since session start" being correct for turn one). Compute
`delta_skill_calls = max(0, skill_calls - prev_skill_calls)` (only when
`skills_loaded is not None`; when it is `None`, the producer is absent
and the delta is meaningless too — keep passing `None` straight
through, unchanged from today), `delta_agent_calls = max(0,
agent_totals.get("calls", 0) - prev_agent_calls)`,
`delta_tool_calls = max(0, tool_totals.get("calls", 0) -
prev_tool_calls)`. Call `_actual_execution_level(
{"calls": delta_skill_calls} if skills_loaded is not None else None,
{"calls": delta_agent_calls}, delta_tool_calls)` in place of today's
call with the raw cumulative values. Do not change what `skills_loaded`,
`agent_totals`, `tools_called`, `api_calls` themselves report in the
returned snapshot — those stay cumulative, matching `run_scope`; only
the three values fed into the execution-level calculation change.
**Rollback:** `git checkout -- .claude/hooks/telemetry/09-telemetry.py`.
**Preconditions:** none.
**Verification:**
- Run: `python tools/run_hook.py telemetry '{"workflow":"test","status":"success"}'`
- Expect: exits 0, and `.claude/hooks/state/telemetry.jsonl` gains one
  new line whose `execution_level.actual` reflects only the calls made
  *since the previous line* (manually diff the new row's
  `skills_loaded.calls`/`agents_spawned.calls`/`api_calls.calls` against
  the prior row's to confirm the delta, not the raw totals, drove the
  label).
- Run: `python -c "import ast; ast.parse(open('.claude/hooks/telemetry/09-telemetry.py', encoding='utf-8').read())"`
- Expect: no `SyntaxError`.
**Done when:** the command above appends a row, and that row's
`execution_level.actual` is computed from this-turn deltas — confirmed
by the red-green test in Task 2, not by eye alone.

**Deviation, reconciled:** the docstring's own "Fire it directly"
example used a stale event family name (`post-run`), a leftover from
before the Notion-merge hook rename — `python tools/run_hook.py
post-run ...` fails with `No hooks for event post-run`. The real family
is `telemetry` (`.claude/hooks/hooks_registry.json`'s `events.telemetry`,
mapped to native `Stop`). Fixed both the docstring's example and this
task's own Verification command above to the working invocation. Fired
for real against the live tree (not a synthetic fixture): the last row
before this fix showed `execution_level: {predicted: E0, actual: E5}`
(stuck); after, `{predicted: E0, actual: E2}` — the delta computation
is confirmed working in the actual environment, not only in the unit
test Task 2 adds.

### Task 2: Prove it with a red-green regression test
**Purpose:** a check that cannot fail is not evidence
(`testing/SKILL.md`'s own rule) — prove the delta fix actually changes
behavior on a long-session-shaped input, not just that it runs.
**Files:**
- Modify: `tools/test_bench.py` (new test block after the existing
  `_actual_execution_level()` tests at line 187)
**Dependencies:** 1 (tests the function Task 1 changes)
**Implementation notes:** Write a synthetic previous `telemetry.jsonl`
row representing "session so far" — `skills_loaded.calls=1,
agents_spawned.calls=4, api_calls.calls=10` — then set the live state
files (`SKILL_COST`/`AGENT_COST`/`TOOL_COST`, monkeypatched to a temp
dir the same way `with_telemetry()` already does at
`tools/test_bench.py:150-161`) to the **cumulative** totals *after*
this turn's real activity of 0 new skill calls, 3 new agent calls, 2
new tool calls: `skills_loaded.calls=1, agents_spawned.calls=7,
api_calls.calls=12`. Call `telemetry_mod.build_snapshot()` and assert
`execution_level.actual == "E4"` — the correct read of *this turn's*
3 agent calls (2-4 range). **The specific regression case:** before
this fix, `build_snapshot()` passed the raw cumulative
`agents_spawned.calls=7` straight into `_actual_execution_level`,
which returns `"E5"` (`>4`) — wrong, because only 3 of those 7 calls
happened this turn. Revert Task 1's change locally, confirm this new
test goes from PASS to FAIL (reproducing `"E5"` where `"E4"` is
expected), then restore Task 1's change and confirm it passes again —
the same red-green discipline `test_bench.py:163-169`'s own comment
already documents for the sibling bug it caught.
**Rollback:** `git checkout -- tools/test_bench.py`.
**Preconditions:** Task 1 complete.
**Verification:**
- Run: `python tools/test_bench.py`
- Expect: `All bench tests passed`, including the new delta-specific
  case.
- Run (temporarily, to prove red-green): revert Task 1's diff only,
  re-run `python tools/test_bench.py`
- Expect: the new test FAILS (reports `E5` where `E4` is expected),
  proving it is not a tautology; then restore Task 1's diff and
  re-confirm green.
**Done when:** `tools/test_bench.py` passes with the new test present,
and the red-green cycle above was actually run and its FAIL output
quoted, not assumed.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Task 2's red-green cycle proves the test can
  fail before trusting it green
- [x] III Smallest change — one function's two internal call
  arguments change; no schema change, no new file, no new mechanism
  (the docstring already licensed exactly this fix)
- [x] IV Reversibility — plain `git revert`; `telemetry.jsonl` is
  gitignored, per-machine, append-only state, unaffected by a code revert
- [x] V No silent degradation — no check is skipped
- [x] VI Mechanism — the fix itself IS the mechanism: a test
  (`tools/test_bench.py`) now asserts the delta behavior, closing the
  gap a written comment alone would leave open
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all boxes ticked)
