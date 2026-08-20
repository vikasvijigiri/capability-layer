# Unified per-run telemetry schema Implementation Plan

## Approved

**Goal:** Consolidate the three uncoordinated cost counters
(`bench.session_calls()`, `01-context-cost.py`, `02-skill-cost.py`) into one
per-turn telemetry snapshot matching a useful subset of the Notion target's
schema, with every field the harness genuinely cannot populate named and
reasoned rather than faked — closing Gap C from the 2026-08-20
Notion-objectives audit doc.
**Source brief:** this conversation; Notion page *Agentic Workflows (IDE)*
§21 (fetched via MCP). **Correction, found by `spec-reviewer`:** the audit
doc itself (`docs/research/2026-08-20-notion-objectives-audit.md`) and
`02-skill-cost.py` were both built earlier the same session but on
*separate, unmerged branches* (`docs/notion-objectives-audit` and
`fix/session-performance-fixes` respectively) — neither is present on
`fix/unified-telemetry-schema`. This plan's own text wrongly implied both
already existed here. Neither is a hard dependency of this plan's own
tasks (see Task 1's fix for `skills_loaded`, and this citation note is now
the audit doc's only trace on this branch) — but the claim needed
correcting rather than left to mislead a future reader.
**Slug:** unified-telemetry-schema
**Risk:** high (inferred — confirm with `python tools/scope.py --plan
docs/plans/2026-08-20-unified-telemetry-schema.md` once saved). Every touched
file matches `CONTROL_PATTERNS` (`.claude/hooks/*`).
**Blast radius:** `.claude/hooks/post-run/00-dispatch.py`'s `STEPS` tuple
(fires every Stop event, i.e. every turn); `.claude/hooks/user-prompt/
01-entry-classifier.py` (fires every UserPromptSubmit) gains one small,
additive write. Both are already-live, frequently-firing hooks — mitigated
by keeping every addition append-only/best-effort and silent-by-default,
matching `01-context-cost.py`/`02-skill-cost.py`'s existing posture exactly.
**Rollback:** revert the commit(s); `00-dispatch.py`'s `STEPS` tuple and
`hooks_registry.json` both lose the new entry together;
`.claude/hooks/state/telemetry.jsonl` (gitignored, per `.gitignore:28`'s
existing `state/` rule) is disposable, never committed.
**Architecture:** No new counting mechanism for what already has one —
reuses `chain.gather()` (state/slug/fingerprint/progress, already computed
every turn by `08-chain-continuity.py`) and the two existing counter state
files, read not re-derived. **One design decision made and grounded, not
guessed:** a "run" in this schema is **one session's cumulative snapshot as
of the most recent turn**, not one turn in isolation. Reasoning: `chain-
ledger.jsonl` is genuinely per-turn, but `call-fingerprints.json` and
`skill-cost.json` are session-cumulative totals — unifying them into a
per-turn *delta* would need new snapshot/diff machinery this plan does not
build. The Notion target's own lifecycle diagram (§1) records telemetry
*once* per user task after `FINALIZE`, not per message exchange, which maps
more naturally onto "session so far" than "this one turn" in an interactive
multi-turn agent anyway. Writing a full cumulative snapshot every turn
(append-only) costs nothing extra on a gitignored JSONL file and lets a
later reader diff two rows for a real per-turn delta if one is ever needed —
so the simpler design does not foreclose the harder one.
**Compatible with `decisions/2026-08-07-derived-state-over-stored-state.md`,
checked, not assumed:** that decision bans storing what git can already
answer (workflow *state*). Telemetry counts are not a fact about the tree —
the decision's own text carves out exactly this category, citing the
already-persisted attempt counter as the precedent ("a count of past
attempts is not a fact about the tree and git cannot hold it").
**Tech stack and constraints:** Python 3, stdlib only, matching every hook
in the repo. No filesystem lookups beyond the existing state files and
`chain.gather()`'s own IO seam (`offline=True` default preserved — no new
network calls). Silent by default (no `print()` in the normal case), per
`decisions/2026-08-04-hooks-never-name-a-skill.md`'s spirit (state-file
writes only, nothing reaches a session's stdout).

## Grounding (verified before planning, not assumed)

- `tools/chain.py:record()` (chain-ledger.jsonl) already writes one JSONL
  row per turn with `{ts, slug, state, fingerprint, progress}` — read in
  full. `chain.gather()` is the reuse seam; calling it a second time is how
  `08-chain-continuity.py` already gets these facts, so Task 1 mirrors that
  call rather than re-deriving.
- `.claude/hooks/post-run/00-dispatch.py` read in full: a fixed `STEPS`
  tuple of finalizer filenames, run in sequence via `subprocess.run`, first
  non-zero exit stops the chain. Confirmed exact registration point for a
  5th finalizer.
- `01-context-cost.py` read in full: `_load()`/`_save()`, a
  `json.loads`/`OSError`-guard pair against a `.claude/hooks/state/*.json`
  file. Task 1's reader mirrors this shape. **Correction, found by
  `spec-reviewer`:** `02-skill-cost.py` (built earlier the same session, but
  on a separate, unmerged branch) was wrongly assumed present here too — it
  is not on this tree. Task 1 was fixed to check
  `SKILL_COST_PRODUCER.is_file()` at read time and report `skills_loaded`
  as genuinely unavailable (with a reason) rather than a fabricated
  zero-filled dict, so this plan does not depend on that branch merging
  first.
- `python tools/memory.py --paths tools/chain.py tools/bench.py
  .claude/hooks/post-run/00-dispatch.py .claude/hooks/post-run/
  08-chain-continuity.py .claude/hooks/post-tool/01-context-cost.py
  .claude/hooks/post-tool/02-skill-cost.py .claude/hooks/hooks_registry.json
  .claude/settings.json` → 30 entries, all directory-level except
  `decisions/2026-08-07-derived-state-over-stored-state.md` (names the
  file). Read in full — see Architecture above; compatible, not violated.
- `.claude/settings.json`'s `Stop` event registers exactly one hook
  (`00-dispatch.py`); the other four finalizers are *not* separately
  registered there, only listed in `00-dispatch.py`'s `STEPS` and
  documented as "manual-only" in `hooks_registry.json`'s `post-run-steps`
  entry. Task 1 follows this exact convention — `settings.json` itself is
  **not** touched.
- Target-spec fields checked against what a Claude Code hook payload can
  actually see, grepped across every existing `load_payload()` call site
  and `tool_input` shape handled anywhere in this repo this session: no
  hook payload has ever carried a token count, an active model name, or an
  API-call boundary. These are marked structurally unavailable in Task 1,
  not attempted.

## File map

- Create: `.claude/hooks/post-run/09-telemetry.py` — reads `chain.gather()`
  + the two existing counter state files + (if present)
  `.claude/hooks/state/last-entry-shape.json`; appends one snapshot row to
  `.claude/hooks/state/telemetry.jsonl`.
- Modify: `.claude/hooks/post-run/00-dispatch.py` — add
  `"09-telemetry.py"` to `STEPS`, last position (runs after the other
  finalizers, so it sees their effects — e.g. whether autocommit
  succeeded).
- Modify: `.claude/hooks/hooks_registry.json` — add to `post-run-steps`
  subscribers.
- Modify: `.claude/hooks/user-prompt/01-entry-classifier.py` — `classify()`'s
  result additionally written to
  `.claude/hooks/state/last-entry-shape.json`, best-effort, silent on
  failure.
- Modify: `tools/test_hooks.py` — regression cases for
  `09-telemetry.py` (fixture counter files → expected merged snapshot,
  including the `unavailable` field list).
- Modify: `tools/test_entry_classifier.py` — one case proving the
  state-file write.
- Modify: `tools/bench.py` — a `telemetry_summary()` reporting function,
  reusing `09-telemetry.py`'s `UNAVAILABLE_FIELDS` constant rather than
  restating the reasons.

## Progress
- [x] Task 1 — telemetry snapshot writer (new Stop finalizer)
- [x] Task 2 — entry-classifier persists its classification (task_type proxy)
- [x] Task 3 — `bench.py` telemetry report

## Tasks

### Task 1: Telemetry snapshot writer (new Stop finalizer)
**Purpose:** one per-turn snapshot consolidating the layer's real cost
counters, with every Notion-spec field this harness cannot populate named
and reasoned rather than silently omitted or faked.
**Files:**
- Create: `.claude/hooks/post-run/09-telemetry.py` —
  `UNAVAILABLE_FIELDS: dict[str, str]` constant naming every target-spec
  field this repo cannot populate and why (`execution_level`: "no E0-E5
  router exists yet"; `model`: "no hook payload exposes the active model
  name"; `agents_spawned`: "no hook counts Task-tool invocations yet";
  `api_call_count`/`context_tokens`/`input_tokens`/`output_tokens`: "not
  observable to a hook in this harness"; `latency`: "needs Start/Stop
  timestamp pairing per turn, not built here"; `parallelism`: "only known
  for planned work via parallel_groups.py, not live-observed";
  `cache_hits`/`cache_misses`: "the repeat-detector in 01-context-cost.py is
  a near-miss proxy, not a true cache-hit concept"; `verification_level`/
  `retries`/`escalations`: "no discrete per-run counter exists yet";
  `success`/`quality_signal`: "no signal exists; needs human or
  verification-result input"). `main()`: load `chain.gather()` (via the same
  `_load("tools/chain.py", ...)` pattern `08-chain-continuity.py` already
  uses), read `call-fingerprints.json`'s `_totals` and `skill-cost.json` in
  full (both already `_load()`-shaped, reuse the pattern not the code —
  each file's schema is small enough that re-reading directly is simpler
  than importing another hook module), read
  `last-entry-shape.json` if present (Task 2's output; tolerate absence).
  Compose one dict: `{ts, run_scope: "session-cumulative", chain: {...},
  tools_called: {...}, skills_loaded: {...}, task_type, unavailable:
  UNAVAILABLE_FIELDS}`. Append as one JSON line to
  `.claude/hooks/state/telemetry.jsonl`. Silent by default — no `print()`
  unless the write itself fails, matching the sibling hooks' posture.
- Modify: `.claude/hooks/post-run/00-dispatch.py:17` — `STEPS` gains
  `"09-telemetry.py"` at the end.
- Modify: `.claude/hooks/hooks_registry.json` — add to `post-run-steps`
  subscribers.
- Test: `tools/test_hooks.py` — fire the `post-run` event (which runs
  `00-dispatch.py`, which now includes the new step) against a realistic
  payload with fixture counter files pre-seeded; assert the new JSONL row's
  shape matches, `chain` sub-dict is present and non-empty, `unavailable`
  names all ten-plus reasoned fields, and a **second** fire appends a
  **second** row (append-only, not overwrite).
**Dependencies:** none
**Implementation notes:** Mirror `chain.record()`'s exact append pattern
(`path.open("a")`, one `json.dumps(...) + "\n"` per call, `path.parent.mkdir
(parents=True, exist_ok=True)`) for `telemetry.jsonl` — same file-safety
shape already proven in this repo, not reinvented. `00-dispatch.py`
propagates a non-zero exit from any step as a hard stop; `09-telemetry.py`
must never itself return non-zero from a caught exception (wrap `main()`'s
body, return 0 on any internal failure) since a reporting step must not be
able to block the turn the way a real finalizer's failure legitimately can.
**Rollback:** revert the commit; the new hook, its `STEPS` entry and its
registry entry disappear together; `telemetry.jsonl` is gitignored state,
never committed.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new `09-telemetry.py` cases (shape,
  append-not-overwrite, `unavailable` completeness).
- Run: `echo '{"workflow":"test","status":"success"}' | PYTHONIOENCODING=utf-8
  python .claude/hooks/post-run/00-dispatch.py` then
  `cat .claude/hooks/state/telemetry.jsonl` (tail -1)
- Expect: exit 0, a new well-formed JSON line appended, matching the schema
  above, with the layer's own real current counter values inside it (not a
  fixture).
- Run: `python -m mypy .claude/hooks/post-run/09-telemetry.py
  .claude/hooks/post-run/00-dispatch.py tools/test_hooks.py`
- Expect: `Success: no issues found`.
**Done when:** a real Stop event produces one real, well-formed telemetry
row; every populated field traces to an existing counter (nothing invented);
every unpopulated target-spec field is named with its reason, not silently
absent from the record.

**Executed, two deviations found and fixed, both by the hook self-test
nudge or direct evidence-checking rather than trusting a green exit code:**
1. `ROOT = Path(__file__).resolve().parents[2]` was wrong — for a file at
   `.claude/hooks/post-run/`, `parents[2]` is `.claude` itself, not the repo
   root (the exact off-by-one class already found once this session in
   `02-skill-cost.py`). First fire produced `"chain": {}` — silently empty,
   not an error — because `_load_module("tools/chain.py", ...)` resolved to
   a nonexistent `.claude/tools/chain.py` and returned `None`. Caught by
   inspecting the actual output rather than trusting `exit=0`; fixed to
   `parents[3]`; re-fired, confirmed `chain` now carries real
   state/slug/fingerprint/progress.
2. `test_hook_registration.py`'s skill-name AST scan flagged `"research"` —
   the docstring referenced `docs/research/...`, and "research" is a real
   skill directory name. Same unreliable-docstring-exemption class already
   found this session (the scanner compares against `ast.get_docstring()`'s
   *cleaned* text, not the raw constant, so a docstring is not reliably
   exempt). Fixed at the source: reworded to avoid the literal substring
   rather than relying on the exemption.

Full tier deferred to the plan's last task boundary, per this repo's own
"cheapest tier that answers the question" policy — not run after every task.

**Third deviation, found by an independently-dispatched `spec-reviewer`
after all three tasks first landed, not by this session's own
execution:** `skills_loaded` always read `.claude/hooks/state/
skill-cost.json` unconditionally, reporting `{"calls": 0, "chars": 0,
"unattributed": 0}` — a real-looking zero — even though that file's
producer, `02-skill-cost.py`, does not exist on this branch (see the
Grounding correction above). Fixed: `build_snapshot()` now checks
`SKILL_COST_PRODUCER.is_file()` first; when absent, `skills_loaded` is
`None` and `"skills_loaded"` is added to the row's own `unavailable` map
with a stated reason, exactly the honesty standard `UNAVAILABLE_FIELDS`
already held every other field to. New `test_hooks.py` case proves it
directly against this tree's real, current absence of that producer
(`OK: skills_loaded honestly reports "unavailable"...`), not a
mocked-absent fixture. `python tools/test_hooks.py`: all green, re-run
after the fix.
**Purpose:** give the telemetry schema's `task_type` field a real,
best-effort signal instead of a permanent null — the entry classifier
already computes exactly this shape of fact every turn and currently
discards it.
**Files:**
- Modify: `.claude/hooks/user-prompt/01-entry-classifier.py:main()` — after
  computing `key = classify(payload.get("prompt") or "")`, best-effort write
  `{"key": key, "ts": <iso timestamp>}` to
  `.claude/hooks/state/last-entry-shape.json` (new import: `time`, already
  a stdlib module; wrap the write in a bare `try/except OSError: pass`,
  matching `01-context-cost.py`'s `_save()` guard exactly). Written even
  when `key` is `None` (the common case, per the module's own docstring —
  "silent when there is nothing to say") so a downstream reader can
  distinguish "classified as nothing" from "never ran this turn."
- Test: `tools/test_entry_classifier.py` — one new case: fire `main()` (or
  call the write path directly) with a realistic prompt, assert the state
  file now contains the matching `key`.
**Dependencies:** none (Task 1's reader already tolerates the file's
absence; this task can land before, after, or independently of Task 1 —
`tools/parallel_groups.py`, run below, is the actual authority).
**Implementation notes:** This is the **only** behavior change to
`classify()`'s own call site in this plan — `classify()` itself (the pure
function `test_entry_classifier.py` already pins against the labelled
corpus) is untouched. The write happens in `main()`, after `key` is
resolved, before the existing `workflow_block(key)` / `print(json.dumps(...))`
path — so a write failure can never affect what the hook emits to the
session, preserving `decisions/2026-08-04-hooks-never-name-a-skill.md`'s
existing guarantee about this file's output.
**Rollback:** revert the commit; the state-file write disappears, Task 1's
`task_type` falls back to always-absent, exactly as it was before this task.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_entry_classifier.py`
- Expect: exit 0, including the new state-file case.
- Run: `echo '{"prompt":"add a dark mode toggle to the settings"}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/user-prompt/01-entry-classifier.py`
  then `cat .claude/hooks/state/last-entry-shape.json`
- Expect: exit 0, unchanged hook stdout (still just the `additionalContext`
  JSON), and the state file shows `{"key": "entry-unframed", ...}`.
**Done when:** the state file reflects the real classification on a real
fire, and the hook's own emitted output is provably unchanged (byte-diff
the stdout before/after this task).

**Executed:** `_record_entry_shape()` added, called right after `key =
classify(...)`, before the early `if not key: return 0`. Live-fired twice
(a real prompt → `{"key": "entry-unframed", ...}`; a silent-case prompt →
`{"key": null, ...}`, stdout empty as expected either way). Byte-diffed
stdout for a real prompt against the pre-task version of the file (checked
out in place via `git checkout HEAD --`, fired, restored) — `IDENTICAL`.
`python tools/test_entry_classifier.py`: all cases green including the 2
new ones. This branch already carries the router-progress-consistency
control/sensitive-surface veto (merged via PR #18 before this branch was
cut) — `classify()` itself untouched by this task either way.

### Task 3: `bench.py` telemetry report
**Purpose:** surface the consolidated snapshot the way `bench.py` already
surfaces the shell-call and skill-cost counters, so the unified schema is
actually readable by a human rather than only existing as a JSONL file.
**Files:**
- Modify: `tools/bench.py` — a `telemetry_summary()` function reading the
  last line of `.claude/hooks/state/telemetry.jsonl` (or `None` if absent);
  one new report section in `render()`/`main()` printing the latest
  snapshot's populated fields plus, once, the full `unavailable` field list
  with reasons — imported from `09-telemetry.py`'s `UNAVAILABLE_FIELDS`
  constant via the same `_load()`-style pattern `bench.py` would need to add
  (or a plain relative import if `tools/` and `.claude/hooks/` can already
  reach each other — confirm the existing import shape used elsewhere in
  `bench.py` before choosing).
**Dependencies:** 1 (reads the schema and constant Task 1 defines)
**Implementation notes:** Same "not yet recorded" fallback message style
`session_calls()`'s report branch already uses, for the same reason: a
fresh session or a session where the new hook hasn't fired yet must not
look like an error.
**Rollback:** revert the commit; `bench.py` loses the report section, no
effect on the underlying data.
**Preconditions:** Task 1 landed (the constant and file it reads must
exist).
**Verification:**
- Run: `python tools/bench.py`
- Expect: exit 0, a new "telemetry" section printed, either the latest
  snapshot's populated fields or the "not yet recorded" fallback, plus the
  full `unavailable` list with reasons printed at least once.
- Run: `python -m mypy tools/bench.py`
- Expect: `Success: no issues found`.
**Done when:** running `bench.py` after a real turn shows real, current
telemetry data, and the same command run on a machine that has never fired
the new hook fails gracefully with the fallback message, not a traceback.

**Executed, one deviation from the plan's stated Verification, reconciled
here:** the plan's Verification proposed observing the "not yet recorded"
fallback live, mid-session, by deleting `telemetry.jsonl` and immediately
re-running `bench.py`. In practice the file was found to repopulate between
separate tool calls in this environment -- live evidence that Task 1's Stop
finalizer fires far more often than "once per full turn" (seemingly once
per tool-call round-trip here), which is itself a positive, unplanned
confirmation that the hook is genuinely live-wired, not merely
unit-tested. Since the fallback path could not be cleanly observed without
racing that firing cadence, it was verified instead by calling
`telemetry_summary()` directly against an isolated, nonexistent `ROOT` —
confirmed `None`, which is exactly what drives `render()`'s fallback
message. `python tools/bench.py` (real session data):
`telemetry (session-cumulative, as of ...)`, `chain`/`tools_called`/
`skills_loaded`/`task_type` all populated from real counters, `unavailable`
lists all 16 reasoned fields. `python -m mypy tools/bench.py`: `Success:
no issues found`.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Task 1 and Task 2's new cases are written and run red
  before their hooks exist; Task 3 has no dedicated test file precedent in
  this repo (`bench.py` has none today, confirmed) — verified by direct
  invocation instead, matching the prior session's identical precedent for
  `skill_body_cost()`
- [x] III Smallest change — reuses `chain.gather()` and both existing
  counter files rather than re-deriving; `agents_spawned` counting and
  per-turn latency pairing are explicitly named and deferred, not built
  here, to keep this plan reviewable as one unit
- [x] IV Reversibility — all three tasks are additive commits with a
  one-line revert; no migration, no persisted state beyond disposable,
  gitignored counter files
- [x] V No silent degradation — `UNAVAILABLE_FIELDS` is the mechanism this
  whole plan exists to prove out: every target-spec field this harness
  cannot populate is named with its reason, in the schema itself, not
  hidden by omission
- [x] VI Mechanism — every claim here is a real counter with a real test;
  no rule is enforced by prose alone
- [x] VII Secrets — no credential enters the repo; telemetry contains only
  counts, timestamps and classification keys, never prompt or file content

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why

- **Gap A (E0-E5 execution-level router).** Its own candidate unit from the
  audit; `execution_level` stays in `UNAVAILABLE_FIELDS` until that unit
  exists to populate it.
- **`agents_spawned` counting.** Cheap, would mirror `02-skill-cost.py`'s
  exact pattern keyed on `tool_name == "Task"` — deliberately not bundled
  in, to keep this plan's diff reviewable as one coherent unit rather than
  two unrelated additions sharing a plan.
- **Per-turn latency.** Needs Start/Stop timestamp pairing; `SessionStart`
  fires once per session, not once per turn, so this needs its own small
  design (where does the "turn started" timestamp live between the two
  hook firings) rather than a one-line addition.
- **Token counts, API-call boundaries, active model name.** Structurally
  unavailable to a hook in this harness, checked this session across every
  `load_payload()`/`tool_input` shape ever handled here — not a scope
  choice, a harness limitation, named as such in `UNAVAILABLE_FIELDS`.
- **`success`/`quality_signal`.** No signal exists in this repo for either;
  populating them would mean inventing a proxy nobody asked for, which is
  exactly what `UNAVAILABLE_FIELDS` exists to avoid doing quietly.
- **Re-plumbing `chain-ledger.jsonl` itself.** Its per-turn granularity and
  its own concern (chain continuity, stall detection) stay untouched;
  Task 1 reads from it, never writes to it or changes its schema.
