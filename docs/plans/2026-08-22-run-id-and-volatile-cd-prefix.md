# Add telemetry run_id and fix the VOLATILE cd-prefix false-repeat bug Implementation Plan

## Approved

Gate 1 approved via `ExitPlanMode`, as 2 of the "fix all 4 remaining
items" request — items 2 (a direct data-analysis pass, no plan) and 4
(already done in PR #32) are handled outside this plan.

**Deviation from `implementation`'s default concurrent-dispatch
behavior** (same reasoning as the prior two units this session):
`parallel_groups.py` reports both tasks schedulable concurrently
(disjoint files), which would normally mean two worktrees and two
`implementer` dispatches. Not done — both are small, independently
verifiable text/logic edits with no coordination risk. Branch
`run-id-and-volatile-cd-prefix`, base commit
`44c789ede1e91769e70634b5f46f3f68a8565413`; both tasks executed
directly and sequentially.

**Goal:** Add a real `run_id` to `09-telemetry.py`'s snapshot (currently
always absent), and fix `01-context-cost.py`'s repeat-detector, whose
`VOLATILE` exclusion list never matches in practice because every real
command in this environment is wrapped as `cd "<dir>" && <command>` —
so legitimately-exempt re-runs (`git status`, `tools/resume.py`,
`tools/bench.py`, `tools/run_checks.py`) are miscounted as wasteful
repeats, inflating the reported duplicate-call rate (objective 5).

**Source brief:** this session's grounded-verdict pass over the 30
primary objectives, and a follow-up root-cause analysis of this
session's own transcript (`~/.claude/projects/.../7bb86612-....jsonl`)
against `01-context-cost.py`'s actual filtering logic.

**Slug:** run-id-and-volatile-cd-prefix

**Risk:** high — forced by `control-surface`. Per `tools/scope.py --plan
docs/plans/2026-08-22-run-id-and-volatile-cd-prefix.md`: `risk: high --
high forced by: control-surface` / `scope: major -- vetoed by:
control-surface, spread`. Gate 2 is still owed regardless.

**Blast radius:** `.claude/hooks/telemetry/09-telemetry.py` (adds one
field, removes one static `UNAVAILABLE_FIELDS` entry — `tools/bench.py`'s
`schema_coverage()` reads `unavailable` dynamically per row, so it
needs no code change, only a different real ratio once `run_id` is
sometimes present). `.claude/hooks/context-budget/01-context-cost.py`
(the repeat-detector `Bash`/`PowerShell` calls go through on every
turn). `tools/test_bench.py` and a new or extended test file for the
context-cost hook.

**Rollback:** `git revert` the commit. `telemetry.jsonl` and
`call-fingerprints.json` are both gitignored, per-machine, append-only
state (`data-analysis/SKILL.md`) — a code revert simply resumes the
prior (less accurate) behavior on the next `Stop`/`PostToolUse` event;
no migration.

**Architecture:**

*Task 1 — `run_id`.* `UNAVAILABLE_FIELDS["run_id"]`'s current reason —
*"this repo's telemetry has no per-user-task run boundary... every row
is session-cumulative"* — is still true in the strict sense: this repo
has no single-invocation "one run" boundary matching the Notion
target's exact concept. But `_chain_facts()` (same file) already
computes `slug` and `fingerprint` — a real, existing identifier for
"which unit of work, at what tree state" — just not exposed under the
`run_id` name. Exposing `f"{slug}:{fingerprint}"` when both are
present is a genuine, honest improvement: it lets a reader group
telemetry rows by unit of work, which is real value, even though it is
not literally "one user task" in the target's strictest sense. The
docstring and the field's own fallback reason must say so plainly —
this is not overclaiming a field the target didn't intend, it is
naming what the existing data actually supports.

**Correction, made before this plan was written:** the previous
session's grounded-verdict pass mischaracterized `cache_hits`/
`cache_misses` as an open "addressable" gap alongside `run_id`. They
are already correctly present in `UNAVAILABLE_FIELDS` with an accurate
reason (*"the repeat-detector in `01-context-cost.py` is a near-miss
proxy, not a true cache-hit concept"*) — confirmed by reading the file
directly before writing this plan. No change needed there; this plan
does not touch them. The real count was 6 fields with a "not yet
built" reason (`run_id`, `escalations`, `parallelism`,
`verification_level`, `success`, `quality_signal`), not 8. Only
`run_id` is in scope here; the other 5 each need their own design
decision about what real signal backs them and stay explicitly out of
scope.

*Task 2 — the VOLATILE cd-prefix bug.* `repeat_notice()` checks
`normalised.startswith(v)` for each `v` in `VOLATILE`. Every real
command observed in this session's transcript is prefixed `cd
"<dir>" && `, so this check can structurally never match — confirmed
by re-running the real function against 159 fingerprint-eligible
real commands from this session's transcript: only 2 were excluded
as volatile (both, on inspection, commands that happened not to be
`cd`-prefixed), while `git status --porcelain`, `python
tools/resume.py`, and similar intentionally-exempt commands were
NOT excluded and counted toward the repeat total. Fix: strip a
leading `cd <path> (&&|;)` from a copy of the normalised command
before the `VOLATILE` check (and before the `MIN_REPEAT_CHARS`
length check, which has the same distortion — a trivial `ls`
wrapped in the `cd` prefix now clears 40 chars on the wrapper alone).
The hash used for actual repeat-fingerprinting is unchanged — it
still hashes the full normalised command, so genuine repeats are
still detected identically; only the VOLATILE/length *exemption*
logic changes.

**Tech stack and constraints:** Plain Python, no new dependency.
`01-context-cost.py` must keep failing open (a broken regex must
never raise and break the `PostToolUse` hook) and must not change
`WARN_CHARS`'s context-cost warning, which correctly uses the full
raw command length (the `cd` wrapper genuinely occupies context, so
that warning should NOT be adjusted). `09-telemetry.py` must not
change `run_scope`'s meaning or any other field's shape.

## Grounding — existing patterns this plan follows

| Category | Pattern | Citation |
|---|---|---|
| `_chain_facts()` already exposes slug+fingerprint | `{"state":..., "slug":..., "fingerprint":..., "progress":...}` | `.claude/hooks/telemetry/09-telemetry.py` (`_chain_facts`) |
| `unavailable` map is read dynamically per row, no schema migration needed | `tools/bench.py:schema_coverage()` | confirmed by reading `schema_coverage()`'s implementation |
| A hook that must never break the turn it observes | `01-context-cost.py`'s own docstring: "Reports, never gates" | `.claude/hooks/context-budget/01-context-cost.py:17-24` |
| Defensive regex/string handling already used in this same file | `re.sub(r"\s+", " ", command).strip()` in `repeat_notice()` | `.claude/hooks/context-budget/01-context-cost.py:150` |
| This repo's own convention for correcting a prior session's mischaracterized finding | stated plainly in the plan's Architecture section, not silently fixed | this plan, above |

`python tools/memory.py --paths .claude/hooks/telemetry/09-telemetry.py
.claude/hooks/context-budget/01-context-cost.py tools/bench.py`
returned only generic `.claude`-directory-level hits (nothing specific
to `run_id` or the VOLATILE-matching question) — no prior attempt or
caution to reconcile with.

## File map

- Modify: `.claude/hooks/telemetry/09-telemetry.py` — add `run_id`,
  remove its static `UNAVAILABLE_FIELDS` entry
- Modify: `.claude/hooks/context-budget/01-context-cost.py` — strip a
  leading `cd <path> (&&|;)` before the `VOLATILE`/`MIN_REPEAT_CHARS`
  checks
- Modify: `tools/test_bench.py` — a case proving `run_id` appears when
  chain facts resolve, and is named in `unavailable` when they do not
- Create: `tools/test_context_cost.py` — this hook has no test file
  today (confirmed: `find . -iname "test_context_cost*"` returns
  nothing); add the minimal regression case for the cd-prefix fix
  rather than leaving a second untested hook in this family

## Progress

- [x] Task 1 — Add `run_id` to the telemetry snapshot
- [x] Task 2 — Fix the VOLATILE cd-prefix false-repeat bug

## Tasks

### Task 1: Add `run_id` to the telemetry snapshot
**Purpose:** close one real, addressable field of objective 22's
schema-coverage gap, honestly — a unit-of-work identifier that already
exists in `_chain_facts()`, just not exposed under the target's name.
**Files:**
- Modify: `.claude/hooks/telemetry/09-telemetry.py:95-97`
  (`UNAVAILABLE_FIELDS["run_id"]` entry)
- Modify: `.claude/hooks/telemetry/09-telemetry.py:234-310`
  (`build_snapshot()`: compute and add `run_id`)
- Modify: `tools/test_bench.py` (new case)
**Dependencies:** none
**Implementation notes:** In `build_snapshot()`, after `chain =
_chain_facts()`: `slug = chain.get("slug")`, `fp =
chain.get("fingerprint")`; if both are truthy strings, `run_id =
f"{slug}:{fp}"`; else `run_id = None` and
`unavailable["run_id"] = ("no active chain state this turn -- slug "
"and/or fingerprint unresolved; see chain.py")`. Add `"run_id": run_id`
to the returned dict (place it near `"chain"` for readability — exact
position does not matter, `json.dumps` output order is not asserted by
any test). Remove the static `"run_id": "this repo's telemetry has no
per-user-task run boundary..."` entry from `UNAVAILABLE_FIELDS` — it
is now a per-row conditional fact computed in `build_snapshot()`, not
a permanent one. Add a one-paragraph comment at the new code
explaining the honesty tradeoff from this plan's Architecture section
(this is a task/tree-state identifier, not a strict single-invocation
"one run" boundary — do not let a future reader assume more than that).
In `tools/test_bench.py`, add a case that monkeypatches `telemetry_mod`'s
`_load_module`/chain-loading path (or, more simply, calls
`telemetry_mod.build_snapshot()` twice — once where `tools/chain.py`
resolves real slug/fingerprint from this actual repo's git state
[already true today, since this repo always has an active branch], and
asserts `run_id` is a non-empty string matching `f"{slug}:{fingerprint}"`
against `_chain_facts()`'s own return value) rather than inventing a
mock chain module.
**Rollback:** `git checkout -- .claude/hooks/telemetry/09-telemetry.py`.
**Preconditions:** none.
**Verification:**
- Run: `python tools/run_hook.py telemetry '{"workflow":"test","status":"success"}'`
- Expect: exits 0; the new last line of `.claude/hooks/state/telemetry.jsonl`
  has a non-null `run_id` field (this repo always has real chain state
  — an active branch — so it will resolve).
- Run: `python tools/test_bench.py`
- Expect: `All bench tests passed`, including the new `run_id` case.
- Run: `python -c "import ast; ast.parse(open('.claude/hooks/telemetry/09-telemetry.py', encoding='utf-8').read())"`
- Expect: no `SyntaxError`.
**Done when:** all three commands pass, and the appended `telemetry.jsonl`
row's `run_id` matches `{slug}:{fingerprint}` from that same row's
`chain` field.

### Task 2: Fix the VOLATILE cd-prefix false-repeat bug
**Purpose:** stop legitimately-exempt re-runs (`git status`,
`tools/resume.py`, `tools/bench.py`, `tools/run_checks.py`) from being
counted as wasteful repeats purely because of the `cd "<dir>" && `
wrapper every real command in this environment carries — the false
positives that inflate the reported duplicate-call rate (objective 5)
without any real repeated work behind them.
**Files:**
- Modify: `.claude/hooks/context-budget/01-context-cost.py:90-96`
  (add a `_CD_PREFIX_RE` constant near `VOLATILE`/`MIN_REPEAT_CHARS`)
- Modify: `.claude/hooks/context-budget/01-context-cost.py:147-177`
  (`repeat_notice()`: strip the prefix before both checks)
- Create: `tools/test_context_cost.py`
**Dependencies:** none (independent of Task 1 — different file)
**Implementation notes:** Add `_CD_PREFIX_RE = re.compile(r'^cd\s+
(?:"[^"]*"|\'[^\']*\'|\S+)\s*(?:&&|;)\s*')` near `VOLATILE`. Add
`_strip_cd_prefix(command: str) -> str: return
_CD_PREFIX_RE.sub("", command, count=1)`. In `repeat_notice()`, after
computing `normalised`, add `check_target =
_strip_cd_prefix(normalised)`. Change the `skip` condition from
`len(command) < MIN_REPEAT_CHARS or any(normalised.startswith(v) for v
in VOLATILE)` to `len(check_target) < MIN_REPEAT_CHARS or
any(check_target.startswith(v) for v in VOLATILE)` — both the length
floor and the VOLATILE check now measure the command with its `cd`
wrapper removed, matching what a person actually typed as the
meaningful part. **Do not change** the hash computed for real
repeat-fingerprinting (`hashlib.sha256(f"{name}\x00{normalised}"...)`)
— it must keep hashing the full `normalised` string (wrapper
included), since that is what actually repeats verbatim in this
environment and changing it risks merging two genuinely different
working-directory contexts into one fingerprint. **Do not change**
`WARN_CHARS`'s context-cost check — the raw command (wrapper included)
is what actually occupies context, so that measurement is correct
as-is.
**Rollback:** `git checkout -- .claude/hooks/context-budget/01-context-cost.py`,
delete `tools/test_context_cost.py`.
**Preconditions:** none.
**Verification:**
- Run: `python tools/run_hook.py context-budget '{"tool_name":"Bash","tool_input":{"command":"cd \"/tmp/x\" && git status --porcelain"}}'`
  twice in a row (event family corrected from the plan's original
  `post-tool` — the real family is `context-budget`, confirmed against
  `hooks_registry.json`; `post-tool` silently runs zero hooks for this
  class, same stale-event-name class of bug as the previous unit's
  `post-run`→`telemetry` fix)
- Expect: exits 0 both times; no `[repeat]` notice on stderr the
  second time (git status is volatile even wrapped in `cd`). **Ran
  live: confirmed silent.**
- Run: same command shape with a genuinely novel, non-volatile
  command, twice in a row
- Expect: the second call DOES print a `[repeat]` notice on stderr —
  proving the fix did not accidentally exempt everything. **Ran live:
  confirmed — `"[repeat] this exact Bash already ran 0s ago
  (occurrence 2): ..."`.**
- Run: `python tools/test_context_cost.py`
- Expect: new test file passes, covering both cases above plus the
  pre-fix regression (temporarily revert this task's diff, confirm the
  git-status case incorrectly produces a `[repeat]` notice, restore).
**Done when:** both manual `run_hook.py` probes above behave as
described, `tools/test_context_cost.py` passes including its
red-green cycle, and `python tools/test_hooks.py` (the whole-hooks
suite) still passes unchanged.

**Housekeeping note, disclosed rather than silently fixed:** the two
live `run_hook.py context-budget` probes above were run against the
REAL `.claude/hooks/state/call-fingerprints.json` before
`tools/test_context_cost.py` existed to isolate against a temp file —
they added a small number of synthetic entries to that live,
gitignored, per-machine counter (`_totals.calls`/`.repeats` moved by a
handful out of 1,444/134). This is diagnostic-only state, not shipped,
not committed, and self-resetting on a fresh install — not worth a
risky surgical removal of specific hash keys with no reliable way to
distinguish them from concurrent legitimate calls in the same window.
`tools/test_context_cost.py` itself uses a temp-file-patched `STATE`
throughout and does not touch the real file.

**Deviation, reconciled:** `python tools/run_checks.py --tier all
--require-test` caught a real consequence of Task 2 adding a new suite
file — `README.md:174` hardcodes a suite count ("45 suites") that
`test_referenced_paths.py` checks against the live count. Fixed to 46
(the new `tools/test_context_cost.py`), not a file this plan originally
declared but a direct, mechanical, checked consequence of Task 2's own
new file.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Task 2 creates a new test file for a
  previously-untested hook and proves it red-then-green against the
  real bug; Task 1's new `test_bench.py` case asserts against real
  `_chain_facts()` output, not an invented value
- [x] III Smallest change — one new field, one regex-based prefix
  strip; no new dependency, no change to hashing or context-cost logic
- [x] IV Reversibility — plain `git revert`; both touched state files
  are gitignored, per-machine, unaffected by a code revert
- [x] V No silent degradation — no check is skipped
- [x] VI Mechanism — both fixes are backed by a new or extended test,
  not a comment alone
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all boxes ticked)
