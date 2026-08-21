# Spec-defined metrics for 4 more objectives — Implementation Plan

## Context

`docs/plans/2026-08-21-three-spec-metrics.md` (merged, PR #24) instrumented
Notion objectives 3, 5, 8 by wiring the Notion spec's own §21 derived-metric
fields into the existing per-turn telemetry hook (`context_read`,
`agents_spawned`, `duplicate_rate`). The user asked, in the same session, to
pick the **maximum number of the remaining 27 objectives that can be
quantifiably optimized** — measured *and* actually improvable via a code
change, not just described — and plan it.

`docs/objectives.md`'s instrument table and `.claude/hooks/post-run/
09-telemetry.py`'s own `UNAVAILABLE_FIELDS` dict (which names every
target-spec field this repo's hooks cannot currently populate, and why) were
read in full this session. Four of those "unavailable" reasons turned out to
be stale rather than structural — the data is either already computed
somewhere and simply not surfaced, or trivially observable once one more
`PostToolUse`/`UserPromptSubmit` matcher is added, mirroring hooks already
merged this week. Objective 2 (tokens) stays explicitly out — `TASK.md`
records it needs a ~$81 paid `eval_triggers.py` run and "its own unit; do
not bundle it." The 15 objectives with no instrument at all (11-13, 15-20,
22, 24-27, 29) stay qualitative — nothing in this repo computes them and
inventing a proxy metric for them would be exactly the "invented proxy"
the prior unit deliberately avoided.

That leaves four objectives buildable right now, each the same shape as the
prior unit's tasks: a small counter hook or a pure read over data that
already exists, wired into `09-telemetry.py`'s snapshot and (where there's a
natural rate) `tools/bench.py`'s report.

## Approved

**Goal:** Instrument objectives 4, 6, 1, and 9/10 using data this repo
either already computes or can observe via one more `PostToolUse`/
`UserPromptSubmit` matcher — no invented proxies, no paid measurement.

**Constraints:** Every addition stays silent-by-default and fail-open,
matching every hook merged this week (`01-context-cost.py`,
`02-skill-cost.py`, `04-read-cost.py`, `05-agent-cost.py`) — a reporting
hook must never block or fail a turn. No new hook may make a network call on
the hot path (every `Stop`/`UserPromptSubmit` fires every turn); Task 4
explicitly stubs `resume.py`'s `_gh_json`, mirroring `chain.gather(offline=
True)`'s own precedent, rather than accidentally taxing every turn with `gh
pr list`. Registration changes only take effect in a fresh session —
confirmed empirically in the 2026-08-20 unit (a live `"*"` matcher added
mid-session produced no new log entry until restart) — so nothing here can
be verified end-to-end this session; each task is verified by firing the
hook script directly, matching the prior unit's own verification style.

**Input:** `docs/objectives.md`; `.claude/hooks/post-run/09-telemetry.py`
(read in full — `UNAVAILABLE_FIELDS`, `build_snapshot()`, `_chain_facts()`);
`.claude/hooks/post-tool/01-context-cost.py`, `04-read-cost.py`,
`05-agent-cost.py` (read in full, the exact pattern every new hook mirrors);
`tools/chain.py:351-392` (`gather()`'s `offline=True` stubbing pattern);
`tools/resume.py` (`gather_facts()` returns `attempts`, `max_attempts`,
`failure_class` already, at lines 487-489); `tools/loop.py` (`rung()`,
`classify_failure`/`failure_budget` via `_hooklib`, pure functions, no IO);
`.claude/hooks/hooks_registry.json` (exact registration shape);
`.claude/settings.json` (confirms matcher `"*"` is valid — used in a live
debug test recorded in `docs/plans/2026-08-20-session-performance-fixes.md`
lines 60-70).

**Output:** three new hooks (`06-tool-cost.py`, `02-turn-timer.py`,
`07-human-cost.py`), one new `09-telemetry.py` read path (no new hook) for
retries/escalations, four new telemetry fields (`api_calls`,
`turn_latency_seconds`, `human_interventions`, `retries`), two of
`UNAVAILABLE_FIELDS`'s stale reasons corrected, `tools/bench.py` gains a
human-readable line for whichever of these has a clean rate, `docs/
objectives.md`'s instrument table updated, four independent commits.

**Done Checks:** `python tools/test_hooks.py` exits 0, including every new
case; each new hook fires correctly against a synthetic payload (commands
given per task); `python tools/run_checks.py --tier all --require-test`
exits 0.

**Out of Scope:** objective 2 (tokens — needs the paid eval run, its own
unit per `TASK.md`); objectives 11-13, 15-20, 22, 24-27, 29 (no instrument
exists and none is invented here — see `docs/research/
2026-08-20-notion-objectives-audit.md`); a live, in-session proof that any
new matcher actually fires (structurally impossible this session, see
Constraints); computing a "human-intervention rate" with an invented
denominator (Task 3 reports raw counts only, same shape as `agents_spawned`,
not a percentage — there is no clean per-task denominator yet, and guessing
one would be exactly the invented-proxy failure mode being avoided).

**Slug:** `four-more-spec-metrics`

**Risk:** high (inferred — confirm with `python tools/scope.py --plan
docs/plans/2026-08-21-four-more-spec-metrics.md` once saved). Every touched
file matches `CONTROL_PATTERNS` (`.claude/hooks/*`, `.claude/settings.json`).

**Blast radius:** `.claude/settings.json` gains 2 `PostToolUse` entries and
1 `UserPromptSubmit` entry; `09-telemetry.py` (fires every `Stop`) gains 4
read paths. Mitigated: every addition mirrors the existing silent,
fail-open, report-only posture exactly — nothing here can deny a tool call
or block a turn, and Task 4's network stubbing prevents a latency
regression on the very turn-cost objective this unit is measuring.

**Rollback:** four independent, additive commits; revert any one without
touching the others. No persisted state beyond disposable, gitignored
counter files (`tool-cost.json`, `turn-timer.json`, `human-cost.json`).

**Architecture:** Tasks 1-3 each add one `PostToolUse`/`UserPromptSubmit`
hook in the exact `_load()`/`_save()` shape `01-context-cost.py` and
`05-agent-cost.py` already use twice over, each writing its own state file
under `.claude/hooks/state/`. Task 4 adds zero new hooks — it is a second
`_load_module()` call inside `09-telemetry.py`, mirroring the existing
`_chain_facts()` helper, reading `resume.gather_facts()`'s already-computed
`attempts`/`max_attempts`/`failure_class` plus `tools/loop.py`'s pure
`rung()` function for the escalation verdict. This is the same "surface,
don't invent" move as the prior plan's Task 3 (`duplicate_rate`).

**Tech stack and constraints:** Python 3, stdlib only, matching every
existing hook.

## Grounding

- `docs/objectives.md`'s instrument table read in full: objectives
  1,2,3,4,5,6,7,8,9,10,14,21,23,28,30 have an instrument; 11-13,15-20,22,
  24-27,29 do not.
- `09-telemetry.py`'s `UNAVAILABLE_FIELDS` read in full. `api_call_count`
  is labeled "not observable to a hook in this harness" — false as stated:
  `.claude/settings.json`'s `PostToolUse` matchers only watch 4 specific
  tool names today (`Bash|PowerShell`, `Read`, `Task`, `Skill`); `Write`,
  `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `NotebookEdit`, and every
  `mcp__*` tool are uncounted, and matcher `"*"` is confirmed valid syntax
  (used in a live debug test, `docs/plans/
  2026-08-20-session-performance-fixes.md:60-70`).
- `latency` is labeled "needs Start/Stop timestamp pairing per turn, not
  built here" — `UserPromptSubmit` (`user-prompt/01-entry-classifier.py`)
  and `Stop` (`post-run/00-dispatch.py`, which runs `09-telemetry.py` last
  in its `STEPS` tuple) both already fire every turn; nothing persists a
  start timestamp today.
- `retries`/`escalations` are labeled "no discrete per-run counter exists
  yet" — also not quite right: `tools/resume.py:487-489` already returns
  `attempts`, `max_attempts`, `failure_class` from `gather_facts()`, and
  `tools/loop.py`'s `rung()` (pure, lines 79-100) turns those plus
  `classify_failure`/`failure_budget` (`_hooklib`) into the same
  repair/restore/rebase/retreat/block verdict `tools/loop.py`'s CLI already
  prints. `tools/chain.py:351-392`'s `gather()` calls `resume.gather_facts`
  too but only re-exports `state`/`slug`/`fingerprint`/`progress` — the
  richer fields are dropped after deriving `state`, so `09-telemetry.py`
  cannot get them from its existing `_chain_facts()` call and must load
  `resume.py` a second time itself, stubbing `_gh_json` the same way
  `chain.gather(offline=True)` already does (`tools/chain.py:370-374`) to
  avoid a live `gh pr list` call on every `Stop`.
- Objective 1 (human interference) has a structural instrument only
  (`tools/test_process_router.py`'s two-gate ownership assertions), no live
  rate. Grepped `.claude/settings.json` for `AskUserQuestion|ExitPlanMode`
  — zero hits, confirming no counter watches either tool today.
- `python tools/memory.py --paths 09-telemetry.py bench.py settings.json
  hooks_registry.json chain.py resume.py loop.py` → all directory-level
  entries, nothing file-specific contradicting this plan (same result the
  prior unit got on an overlapping path set).

## File map

- Create: `.claude/hooks/post-tool/06-tool-cost.py` — total tool-call
  counter, Task 1 (objective 4).
- Create: `.claude/hooks/user-prompt/02-turn-timer.py` — per-turn start
  timestamp, Task 2 (objective 6).
- Create: `.claude/hooks/post-tool/07-human-cost.py` — human-gate counter,
  Task 3 (objective 1).
- Modify: `.claude/settings.json`, `.claude/hooks/hooks_registry.json` —
  register all three new hooks.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — 4 new snapshot fields
  (`api_calls`, `turn_latency_seconds`, `human_interventions`, `retries`);
  correct 3 `UNAVAILABLE_FIELDS` entries (`api_call_count`, `latency`,
  `retries`/`escalations`).
- Modify: `tools/bench.py` — surface `api_calls` (total tool calls this
  session) next to the existing shell-call line.
- Modify: `tools/test_hooks.py` — regression cases for all three new hooks
  plus the `09-telemetry.py` retries read-path.
- Modify: `docs/objectives.md` — instrument table gains rows for the newly
  measurable objectives.

## Progress
- [ ] Task 1 — total tool-call counter (objective 4, `api_calls`)
- [ ] Task 2 — per-turn latency (objective 6, `turn_latency_seconds`)
- [ ] Task 3 — human-intervention counter (objective 1, `human_interventions`)
- [ ] Task 4 — surface retry/escalation facts (objectives 9/10, `retries`)

## Tasks

### Task 1: Total tool-call counter (objective 4)
**Purpose:** complete the spec's `tool_calls`/`api_call_count` pair — today
only 4 of the many `PostToolUse`-observable tool names are counted at all,
so objective 4 has been gradable only for a slice of real tool use.
**Files:**
- Create: `.claude/hooks/post-tool/06-tool-cost.py` — `WATCHED = None`
  (fires on every tool, matcher does the filtering); on any payload,
  accumulate `{"calls": int, "by_tool": {tool_name: count}}` in
  `.claude/hooks/state/tool-cost.json`, mirroring `05-agent-cost.py`'s
  `_load()`/`_save()` shape. Separate state file from
  `call-fingerprints.json` on purpose (same reasoning as `02-skill-cost.py`'s
  docstring): this is a total-calls tally across every tool, not a
  per-command fingerprint/repeat check.
- Modify: `.claude/settings.json` — new `PostToolUse` entry, `"matcher":
  "*"`.
- Modify: `.claude/hooks/hooks_registry.json` — `post-tool.subscribers`
  gains the file; `claude_code_event` string extended to note "all tools,
  via `*`".
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new `api_calls` field
  (`{"calls": int, "by_tool": dict}`); remove `api_call_count` from
  `UNAVAILABLE_FIELDS`.
- Test: `tools/test_hooks.py` — a synthetic `Bash` payload and a synthetic
  `mcp__github__get_me` payload both increment `calls` and their own
  `by_tool` entry; two different tool names produce two `by_tool` keys.
**Dependencies:** none.
**Implementation notes:** Every existing counter (`01-context-cost.py`,
`04-read-cost.py`, `05-agent-cost.py`, `02-skill-cost.py`) keeps running
unchanged — this is additive, not a replacement, so `api_calls.calls` will
be >= the sum of the narrower counters, not equal to it (this hook also
counts `Write`, `Edit`, `Grep`, `Glob`, MCP tools, etc. that nothing else
sees).
**Rollback:** revert the commit; hook, registration, and telemetry field
disappear together.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new tool-cost cases.
- Run: `echo '{"tool_name":"mcp__github__get_me","tool_input":{}}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/post-tool/06-tool-cost.py`
  then `cat .claude/hooks/state/tool-cost.json`
- Expect: `calls: 1`, `by_tool: {"mcp__github__get_me": 1}`.
**Done when:** a tool name none of the other 4 counters watch (e.g. `Grep`,
or any `mcp__*` name) is counted for the first time anywhere in this repo.

### Task 2: Per-turn latency (objective 6)
**Purpose:** close the named gap in `09-telemetry.py`'s own
`UNAVAILABLE_FIELDS`: "`latency`: needs Start/Stop timestamp pairing per
turn, not built here." `tools/bench.py` only times the check-tier subprocess,
never the turn itself.
**Files:**
- Create: `.claude/hooks/user-prompt/02-turn-timer.py` — on every
  `UserPromptSubmit`, overwrite `.claude/hooks/state/turn-timer.json` with
  `{"started_at": time.time()}`. One active turn at a time, so overwrite
  (not accumulate) is correct — mirrors `01-entry-classifier.py`'s own
  posture of firing once per turn with no accumulation.
- Modify: `.claude/settings.json` — new `UserPromptSubmit` entry, alongside
  the existing `01-entry-classifier.py` entry.
- Modify: `.claude/hooks/hooks_registry.json` — `user-prompt.subscribers`
  gains the file.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new `_turn_latency()`
  helper reads `turn-timer.json`'s `started_at`; `turn_latency_seconds` =
  `time.time() - started_at` if present, else `None` with a reason kept in
  `unavailable` for that one snapshot (first turn of a session, before the
  timer has ever written). Remove `latency` from `UNAVAILABLE_FIELDS`.
- Test: `tools/test_hooks.py` — the timer hook writes a fresh timestamp on
  each fire (overwrite, not append); a synthetic `09-telemetry.py` call with
  a known `started_at` produces a `turn_latency_seconds` within a tight
  tolerance of the real elapsed time.
**Dependencies:** none.
**Implementation notes:** `Stop` (`post-run/00-dispatch.py`) already runs
`09-telemetry.py` last in its `STEPS` tuple, so no new `Stop` registration
is needed — Task 2 only adds the `UserPromptSubmit` side.
**Rollback:** revert the commit; hook, registration, and telemetry field
disappear together; `09-telemetry.py`'s snapshot silently loses the field
via the existing `unavailable`-map fallback.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new turn-timer cases.
- Run: `echo '{}' | PYTHONIOENCODING=utf-8 python
  .claude/hooks/user-prompt/02-turn-timer.py` then `cat
  .claude/hooks/state/turn-timer.json`
- Expect: a `started_at` close to the current Unix time.
**Done when:** `09-telemetry.py`'s snapshot carries a real
`turn_latency_seconds` for any turn where the timer fired first, and states
plainly (via `unavailable`) when it did not.

### Task 3: Human-intervention counter (objective 1)
**Purpose:** objective 1 ("ask only when the system genuinely cannot
proceed safely or correctly") has only a structural instrument today
(`test_process_router.py`'s two-gate ownership assertions) — nothing counts
how often either gate actually fires in a real session.
**Files:**
- Create: `.claude/hooks/post-tool/07-human-cost.py` — `WATCHED =
  ("AskUserQuestion", "ExitPlanMode")`; on match, accumulate `{"calls": int,
  "by_tool": {"AskUserQuestion": n, "ExitPlanMode": n}}` in
  `.claude/hooks/state/human-cost.json`, mirroring `05-agent-cost.py`'s
  shape exactly.
- Modify: `.claude/settings.json` — new `PostToolUse` entry, matcher
  `"AskUserQuestion|ExitPlanMode"`.
- Modify: `.claude/hooks/hooks_registry.json` — `post-tool.subscribers`
  gains the file.
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new
  `human_interventions` field (raw counts, no invented rate/denominator —
  see Out of Scope).
- Test: `tools/test_hooks.py` — an `AskUserQuestion` payload and an
  `ExitPlanMode` payload each increment `calls` and their own `by_tool`
  key; a non-matching tool (`Bash`) is ignored.
**Dependencies:** none.
**Implementation notes:** Deliberately two tool names on one hook (not two
hooks) — both are gate mechanisms per `.claude/operating.md` ("Two approval
gates, each with its own tool: Gate 1 `ExitPlanMode`, Gate 2
`AskUserQuestion`"), so one counter with a `by_tool` breakdown answers "how
often did either gate fire" without forcing a caller to sum two files.
**Rollback:** revert the commit; hook, registration, and telemetry field
disappear together.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new human-cost cases.
- Run: `echo '{"tool_name":"ExitPlanMode","tool_input":{}}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/post-tool/07-human-cost.py`
  then `cat .claude/hooks/state/human-cost.json`
- Expect: `calls: 1`, `ExitPlanMode: 1`.
**Done when:** a real Gate 1 or Gate 2 firing is counted for the first time
anywhere in this repo.

### Task 4: Surface retry/escalation facts (objectives 9/10)
**Purpose:** `09-telemetry.py` labels `retries` and `escalations` "no
discrete per-run counter exists yet" — the ledger already carries
`attempts`/`max_attempts`/`failure_class` per active plan and
`tools/loop.py`'s `rung()` already turns those into the same
repair/restore/rebase/retreat/block verdict its CLI prints; nothing wires
either into the per-turn snapshot.
**Files:**
- Modify: `.claude/hooks/post-run/09-telemetry.py` — new `_retry_facts()`
  helper: loads `tools/resume.py` via the same `_load_module()` helper
  `_chain_facts()` already uses, stubs `resume._gh_json = lambda *a, **k:
  None` (mirroring `tools/chain.py:370-374`'s `offline=True` pattern, so no
  turn ever pays for a live `gh pr list` call), then calls
  `resume.gather_facts(ROOT, slug)` using the slug `_chain_facts()` already
  resolved. Extracts `attempts`, `max_attempts`, `failure_class`. Where a
  `failure_class` is present, also loads `tools/loop.py` the same way and
  calls its pure `rung(kind, attempt, budget, restored=.., has_green=..)`
  (via `_hooklib.classify_failure`/`failure_budget` for `kind`/`budget`) to
  get the escalation verdict. New `retries` field: `{"attempts": int,
  "max_attempts": int, "failure_class": str | None, "rung": str | None}`.
  Remove `retries`/`escalations` from `UNAVAILABLE_FIELDS`.
- Test: `tools/test_hooks.py` — a fixture ledger with `attempts: 2,
  failure_class: "deterministic"` produces the same `rung` value
  `tools/loop.py --json` would print for identical inputs (hand-verified
  against `rung()`'s own table); a ledger with no active plan (`slug` is
  `None`) produces `retries: {"attempts": 0, "max_attempts": 0,
  "failure_class": None, "rung": None}`, not an exception.
**Dependencies:** none.
**Implementation notes:** Reads only; touches `09-telemetry.py` in a field
non-overlapping with Tasks 1-3's. This is the one task with no new hook — pure
read-and-compute over data two other tools already own. The offline stub is
load-bearing: without it, this task would make `09-telemetry.py` slower on
every single turn, directly working against objective 6 (Task 2) on the
same unit.
**Rollback:** revert the commit; the field disappears, `resume.py`/
`loop.py` are untouched.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the new retry-facts case.
- Run: `python tools/loop.py --json` on a branch with an active plan and
  compare its `rung`/`attempt`/`budget` fields by hand against
  `09-telemetry.py`'s next-fired `retries` entry in `telemetry.jsonl`.
- Expect: identical values for the same tree state.
**Done when:** the same rung `tools/loop.py`'s CLI already prints is also
in `telemetry.jsonl`, unprompted, on every turn a plan is active.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — each hook's cases are written and run red before the
  hook exists
- [x] III Smallest change — Task 4 adds zero new hooks/counters, only reads
  data two existing tools already compute; Tasks 1-3 each mirror an
  already-proven pattern exactly
- [x] IV Reversibility — four independent, additive commits
- [x] V No silent degradation — Task 2's missing-timer case and Task 4's
  no-active-plan case both degrade to a named, structured absence, never a
  guessed value
- [x] VI Mechanism — every number comes from a real counter, hook, or
  pre-existing pure function, never restated from memory
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why

- **Objective 2 (tokens).** `TASK.md`/`HANDOFF.md` record it needs a ~$81
  paid `eval_triggers.py` run and explicitly "its own unit; do not bundle
  it." Untouched here.
- **Objectives 11-13, 15-20, 22, 24-27, 29 (15 objectives).** No instrument
  exists for any of them (`docs/objectives.md`), and the qualitative pass
  in `docs/research/2026-08-20-notion-objectives-audit.md` names what would
  make each measurable — none of those mechanisms exist in this repo yet.
  Inventing a proxy for any of them here would repeat exactly the mistake
  the prior unit's Task 1 was careful to label, not repeat.
- **A live, in-session proof that any new matcher fires.** Structurally
  impossible: `.claude/settings.json` hook registrations load once per
  session (empirically confirmed 2026-08-20). Each task is instead verified
  by firing its script directly against a synthetic payload, same as every
  prior hook this week — a real end-to-end check is the first item for
  whoever opens the next fresh session, same caveat the prior plan's Task 2
  carried for `02-skill-cost.py`.
- **An invented "human-intervention rate" denominator (Task 3).** The
  spec's own §21 names the field but not a denominator; guessing one (calls
  per session? per chain unit? per turn?) would be a proxy nobody asked for.
  Task 3 reports raw counts, matching `agents_spawned`'s own already-shipped
  shape.
- **Objective 7 (compute/cost).** Already has an instrument
  (`model:` frontmatter across skills/agents, per `docs/objectives.md`) that
  needs no new counter — nothing to add here.
