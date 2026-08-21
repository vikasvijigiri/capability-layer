# Spec-defined metrics for 3 objectives Implementation Plan

## Approved

**Goal:** Instrument objectives 3, 8, 5 using the Notion spec's own §21
derived metrics (not invented proxies), wired into the existing per-turn
telemetry hook so each accumulates automatically going forward.

**Source brief:** this conversation; Notion §21 (fetched via MCP earlier
this session); `docs/research/2026-08-20-notion-objectives-audit.md`

**Slug:** three-spec-metrics

**Risk:** high (inferred — confirm with `python tools/scope.py --plan
docs/plans/2026-08-21-three-spec-metrics.md` once saved). Every touched
file matches `CONTROL_PATTERNS` (`.claude/hooks/*`).

**Blast radius:** `01-context-cost.py` (fires every Bash/PowerShell call)
gains a `Read`-watching sibling; a new hook watches `Task` (agent spawns);
`09-telemetry.py` (fires every Stop) gains 3 fields. Mitigated: every
addition mirrors the existing silent-by-default, fail-open posture exactly
— no new hook can block a turn.

**Rollback:** three independent, additive commits; revert any one without
touching the others. No persisted state beyond disposable, gitignored
counter files.

**Architecture:** §21's raw fields map directly: `context_tokens` (Task 1),
`agents_spawned` (Task 2), `repeated_operations_avoided` (Task 3, already
partially wired). None require inventing a new schema — each is one more
`_load()`/`_save()` counter in the exact shape `01-context-cost.py` and
`09-telemetry.py` already use twice over. **Honest limitation carried into
Task 1's own docstring**: `context_tokens` itself is confirmed
unmeasurable by any Claude Code hook payload; the counter approximates it
via `Read`-file byte size, labeled a proxy, not the real field.

**Tech stack and constraints:** Python 3, stdlib only. `02-skill-cost.py`
(the pattern Task 2 mirrors) does not exist on this branch — it ships on
`fix/session-performance-fixes`, still unmerged — so Task 2 recreates its
shape from the pattern rather than importing it; noted so the citation
isn't mistaken for a live file on this tree.

## Grounding

- `01-context-cost.py` read in full (again, for Task 1's exact insertion
  point): `WATCHED = ("Bash", "PowerShell")`, `WARN_CHARS = 700`,
  `_load()`/`_save()` against `.claude/hooks/state/call-fingerprints.json`.
  Its own `_totals` dict already carries `repeats`/`calls` — Task 3's
  metric is arithmetic over data that already exists, not a new counter.
- Live-measured this session, not asserted: duplicate-operation rate
  `1/17 = 5%` (`call-fingerprints.json`'s current `_totals`, at the time of
  measurement).
- `09-telemetry.py` read in full: `build_snapshot()` already merges
  `call-fingerprints.json` and (conditionally, if present) `skill-cost.json`
  into one snapshot — the exact seam Tasks 1-3 extend.
- `.claude/settings.json`'s `PostToolUse` array already has `Bash|PowerShell`
  and `Skill` matcher entries (from earlier this session) — Task 1 adds to
  the existing array; Task 2 adds a `Task`-matcher entry alongside them.
- `python tools/memory.py --paths 01-context-cost.py 09-telemetry.py
  bench.py settings.json hooks_registry.json` → 30 entries, all
  directory-level, nothing file-specific contradicting this plan.

## File map

- Create: `.claude/hooks/post-tool/04-read-cost.py` — `Read`-tool byte
  counter, Task 1.
- Create: `.claude/hooks/post-tool/05-agent-cost.py` — `Task`-tool (agent
  spawn) counter, Task 2.
- Modify: `.claude/settings.json`, `.claude/hooks/hooks_registry.json` —
  register both new hooks under `post-tool`.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — read both new counter
  files plus the existing `repeats`/`calls` pair into 3 new snapshot
  fields: `context_read`, `agents_spawned`, `duplicate_rate`.
- Modify: `tools/bench.py` — surface `duplicate_rate` as a named,
  human-readable rate in the existing report (the number is already
  computed for `session_calls()`'s repeat count; it has just never been
  shown as a percentage).
- Modify: `tools/test_hooks.py` — regression cases for both new hooks and
  the 3 new telemetry fields.

## Progress
- [x] Task 1 — `Read`-tool context counter (objective 3, proxy for
  `context_tokens`). **Executed:** `04-read-cost.py` created, registered in
  `settings.json`/`hooks_registry.json`, wired into `09-telemetry.py`'s
  `context_read` field. `python tools/test_hooks.py` green; fired directly
  against `README.md`, `chars: 13042` matched `wc -c` exactly.
- [x] Task 2 — agent-spawn counter (objective 8, `agents_spawned`).
  **Executed:** `05-agent-cost.py` created, registered, wired into
  `09-telemetry.py`'s `agents_spawned` field. Fired directly with
  `subagent_type: test-verifier` → `{"calls": 1, "by_type": {"test-verifier":
  1}}`. `agents_spawned` removed from `UNAVAILABLE_FIELDS`.
- [x] Task 3 — surface duplicate-operation rate (objective 5, already
  partially wired). **Executed:** `tools/bench.py` now prints
  `duplicate-operation rate: 26% (4/15)`, matching `call-fingerprints.json`'s
  live totals by hand-calculation; `09-telemetry.py` gained `duplicate_rate`.

## Tasks

### Task 1: `Read`-tool context counter (objective 3)
**Purpose:** approximate the spec's `context_tokens` field — genuinely
unmeasurable directly — via the closest observable proxy: bytes of file
content a `Read` call adds to permanent context.

**Files:**
- Create: `.claude/hooks/post-tool/04-read-cost.py` — `WATCHED = ("Read",)`;
  on match, resolve `tool_input.get("file_path")`, `Path(path).stat().st_size`
  if the file exists (0 + no error if not — a nonexistent path is not this
  hook's problem to diagnose); warn at `WARN_CHARS = 700` (same threshold,
  named as a shared constant in a comment pointing at
  `01-context-cost.py:63` rather than silently duplicated); accumulate
  `{"calls": int, "chars": int}` in `.claude/hooks/state/read-cost.json`.
  Docstring states plainly: file-on-disk size is a proxy for "what the
  harness actually inserted into context" (truncation, line numbers not
  accounted for), not the real number.
- Modify: `.claude/settings.json` — new `PostToolUse` entry, matcher
  `"Read"`.
- Modify: `.claude/hooks/hooks_registry.json` — `post-tool.subscribers`
  gains the file.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new `context_read`
  field in `build_snapshot()`, same `_load_json()` pattern as the other
  two counters.
- Test: `tools/test_hooks.py` — a real file over 700 bytes warns; a small
  file does not; a nonexistent path returns 0 chars, not an error; totals
  accumulate across two fires.

**Dependencies:** none

**Implementation notes:** Mirror `01-context-cost.py`'s `_load()`/`_save()`
byte-for-byte in shape (already proven 3 times this session).

**Rollback:** revert the commit; hook, registration, and telemetry field
disappear together.

**Preconditions:** none.

**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new Read-cost cases.
- Run: `echo '{"tool_name":"Read","tool_input":{"file_path":"README.md"}}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/post-tool/04-read-cost.py`
  then `cat .claude/hooks/state/read-cost.json`
- Expect: `chars` matches `README.md`'s real size (cross-check `wc -c`).

**Done when:** a real `Read` call produces a real, verifiable byte count;
the docstring's proxy-not-exact framing is explicit, not implied.

### Task 2: Agent-spawn counter (objective 8, `agents_spawned`)
**Purpose:** `agents_spawned` has zero tracking anywhere in this repo —
the spec's own `tool_calls/task` + `agents_spawned/task` pair is how
objective 8 ("minimum-sufficient execution graph") is meant to be graded,
and only half of that pair currently exists.

**Files:**
- Create: `.claude/hooks/post-tool/05-agent-cost.py` — `WATCHED = ("Task",)`;
  on match, read `tool_input.get("subagent_type")` if present (best-effort,
  not required); accumulate `{"calls": int}` (and, if a type was found, a
  per-type breakdown dict) in `.claude/hooks/state/agent-cost.json`.
- Modify: `.claude/settings.json` — new `PostToolUse` entry, matcher
  `"Task"`.
- Modify: `.claude/hooks/hooks_registry.json` — `post-tool.subscribers`
  gains the file.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new `agents_spawned`
  field.
- Test: `tools/test_hooks.py` — a `Task` call increments `calls`; a
  non-Task tool is ignored; the per-type breakdown records
  `subagent_type` when present.

**Dependencies:** none (independent files from Task 1; both touch
`09-telemetry.py`'s schema in non-overlapping fields — `parallel_groups.py`,
run below, is the actual authority on scheduling).

**Implementation notes:** Recreates `02-skill-cost.py`'s exact
`_load()`/`_save()` shape from memory of building it earlier this session
— that file does not exist on this branch (see Tech stack note above), so
this is a pattern match, not an import or a read of a live sibling file.

**Rollback:** revert the commit; hook, registration, and telemetry field
disappear together.

**Preconditions:** none.

**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new agent-cost cases.
- Run: `echo '{"tool_name":"Task","tool_input":{"subagent_type":"test-verifier"}}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/post-tool/05-agent-cost.py`
  then `cat .claude/hooks/state/agent-cost.json`
- Expect: `calls: 1`, `test-verifier` recorded.

**Done when:** a real `Task` dispatch is counted; baseline moves from
"zero tracking, anywhere" to a real, current number.

### Task 3: Surface duplicate-operation rate (objective 5)
**Purpose:** the spec's `Duplicate-operation rate` is already computed
(`repeats`/`calls` in `call-fingerprints.json`'s `_totals`) and `bench.py`
already showed it as an unlabeled percentage (`repeats: N (pct%)`) -- this
task relabels it under the spec's own §21 term and adds the same number to
`09-telemetry.py`'s per-run snapshot, where it did not appear at all.

**Files:**
- Modify: `tools/bench.py` — in the existing `session_calls()` report
  block, add the rate as a percentage, explicitly labeled
  `duplicate-operation rate` (the spec's own term).
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new
  `duplicate_rate` field (`repeats/calls`, `0.0` if `calls == 0`).
- Test: `tools/test_hooks.py` — the telemetry row's `duplicate_rate`
  matches a hand-computed value from fixture `_totals`.

**Dependencies:** none.

**Implementation notes:** Pure arithmetic over existing data — no new
counter, no new hook.

**Rollback:** revert the commit; the label disappears, the underlying
data (already existed before this plan) is unaffected.

**Preconditions:** none.

**Verification:**
- Run: `python tools/bench.py`
- Expect: a line naming `duplicate-operation rate` with a real percentage,
  matching `call-fingerprints.json`'s live `_totals` by hand-calculation.
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new rate-calculation case.

**Done when:** the same number this session already measured by hand
(`1/17 = 5%`) is what `bench.py` now prints unprompted.

## Deviations from plan

- Two pre-existing `tools/test_hooks.py` cases broke as a direct, correct
  consequence of Task 2/1 and were reconciled in place rather than left for a
  reviewer: `_EXPECTED_UNAVAILABLE_KEYS` dropped `agents_spawned` (it is now
  measured, not unavailable); the "non-watched tool_name" case for
  `01-context-cost.py` was narrowed to check only that hook's own state file,
  since `04-read-cost.py` now legitimately shares the `post-tool` directory
  and fires stderr on the same `Read` payload.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — each hook's cases are written and run red before the
  hook exists
- [x] III Smallest change — Task 3 adds zero new counters, only surfaces
  existing data; Tasks 1/2 each mirror an already-proven pattern exactly
- [x] IV Reversibility — three independent, additive commits
- [x] V No silent degradation — Task 1's proxy-not-exact limitation is
  stated in the hook's own docstring, not implied
- [x] VI Mechanism — every number comes from a real counter or hook, never
  restated from memory
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why

- **A 4th counter for `Grep`/`Glob`.** Same class as `Read`, not in this
  plan's 3 chosen objectives.
- **Task-boundary segmentation** (computing `tool_calls/task` rather than
  `tool_calls/session`). The harness has no clean "task started/ended"
  signal beyond `chain.py`'s plan-slug transitions, which is a separate,
  larger design question this plan does not open.
- **Objective 12** (production-grade) — dropped from this round; the spec
  names no direct metric for it, per this session's own research finding.
