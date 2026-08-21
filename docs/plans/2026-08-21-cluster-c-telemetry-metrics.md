# Cluster C — instruments for objectives 22, 24, 18 Implementation Plan

## Approved

## Context

`docs/objectives.md` names a live instrument for 15 of the Notion spec's 30
Primary Objectives. The other 15 are graded once, qualitatively, by
`docs/research/2026-08-20-notion-objectives-audit.md` — real evidence, but
nothing that can re-run to catch regression. The user asked for a plan to
instrument the remaining 15, requiring every metric to be **defensible**
(traceable to something already computed, a comparable real project's own
conformance vocabulary, or a structural fact) and **additive** (no existing
objective's grade may regress).

`brainstormer` was dispatched first, since which mechanism proves each of 15
different qualitative objectives was genuinely undecided. Its output,
`docs/specs/2026-08-21-qualitative-objective-metrics.md`, grouped the 15 into
four clusters and recommended building **Cluster C first** — objectives 22
(observable and auditable), 24 (self-adapting and self-healing), and 18
(adaptive, not prescriptive) — because all three are pure reads over data
`.claude/hooks/post-run/09-telemetry.py` and `docs/evals/trigger-queries.json`
already produce, need no new hook, and two of the three metrics need almost
no new machinery.

This plan reads the spec's Cluster C section as its brief, then corrects two
places the spec's design was imprecise once the actual code was read (C1's
own requirement) — recorded below, not silently implemented around.

## Approved

**Goal:** Give objectives 22, 24 and 18 a real, re-runnable instrument each —
schema coverage and trace completeness for 22, a local-repair ratio for 24,
and a full-corpus route-presence check plus a fallback-safety check for 18 —
using only data `09-telemetry.py` and the existing trigger-queries corpus
already produce, with zero new hooks and zero per-turn cost.

**Constraints:** Additive only — no existing gate, hook, check, or shipped
telemetry field changes behaviour; no existing objective's grade may regress.
Off the hot path — `09-telemetry.py` already fires on `Stop` every turn
(unchanged by this plan); Task 1 adds two dictionary entries to a constant it
already defines, never a new hook subscriber or new work on `PostToolUse` or
`UserPromptSubmit`. Every new *check* (as opposed to that one constant edit)
lands in the `test` tier or a `tools/bench.py` read invoked on demand — none
of them runs on any lifecycle event at all. Report before gate — each new
check prints a ratio and exits 0; turning any of them into a release-blocking
gate is a follow-up unit,
after a baseline exists (`docs/specs/2026-08-21-qualitative-objective-metrics.md`'s
own "Report before gate", mirroring `bench.py --save`'s "baselines
comparisons, never judges"). Python 3, stdlib only — no new dependency. Every
new check must be proven capable of failing (a seeded-violation test) before
it is trusted, per this repository's Article II and the specific defence
against the deleted `03-review-gate`'s self-invalidating-receipt failure mode.

**Input:** `docs/specs/2026-08-21-qualitative-objective-metrics.md`'s Cluster C
section (the brief this plan executes); `.claude/hooks/post-run/09-telemetry.py`
(`build_snapshot()`, `UNAVAILABLE_FIELDS`, the `chain`/`retries` fields — all
read in full this session, including this session's own additions); `tools/bench.py`
(`session_calls()`/`total_tool_calls()`/`skill_body_cost()`'s
read-a-state-file-and-report shape, mirrored exactly); `.claude/hooks/user-prompt/01-entry-classifier.py`
(`classify()`, `_load()`, `_control_or_sensitive_patterns()` at lines
331-355, `_names_control_or_sensitive_path()` — read in full); `tools/test_entry_classifier.py`
(345 lines, already replays `docs/evals/trigger-queries.json` through
`classify()` for the two entry-shape stages — read in full, extended rather
than duplicated); `tools/scope.py` (`CONTROL_PATTERNS`/`SENSITIVE_PATTERNS`
at lines 66/90).

**Output:** `09-telemetry.py` gains two `UNAVAILABLE_FIELDS` entries
(`run_id`, `escalations` — named honest gaps, not fabricated values) and a
`SPEC_FIELD_COUNT` constant documenting the §21 field-count this repo's
coverage ratio is computed against; `tools/bench.py` gains
`schema_coverage()` and `local_repair_ratio()`, each surfaced in `render()`;
`tools/test_bench.py` (new file) with regression cases for both, each proven
to fail on a seeded violation; `tools/test_entry_classifier.py` gains a
full-corpus route-presence check and a fallback-safety check for objective
18; `docs/objectives.md`'s instrument table gains rows for 18, 22, 24.

**Done Checks:** `python tools/run_checks.py --tier all --require-test` exits
0; `python tools/test_bench.py` exits 0 including both seeded-violation cases;
`python tools/test_entry_classifier.py` exits 0 including the new
route-presence and fallback-safety cases.

**Out of Scope:** Clusters A (target-matrix conformance: 13, 15, 16, 25, 27),
B (re-run safety: 17, 19, 20 — both open design questions the spec left
unresolved belong to B and A, not this plan), and D (layer self-grading: 11,
12, 26, 29) — each is its own future unit per the spec's own decomposition. Turning
any of this plan's three new checks into a release-blocking gate. The E0-E5
execution-level router and the agent-catalogue decision record — both
confirmed non-blocking, separate candidate units in the spec's own "Two loose
threads" section. Re-grading objectives 1-10. Objective 2 (needs the ~$81
paid `eval_triggers.py` run, its own unit per `TASK.md`).

**Slug:** `cluster-c-telemetry-metrics`

**Risk:** high — `python tools/scope.py --plan
docs/plans/2026-08-21-cluster-c-telemetry-metrics.md`: "high forced by:
control-surface, shared-surface". `.claude/hooks/post-run/09-telemetry.py`
and `.claude/project-checks.json` are both control-surface paths.

**Blast radius:** `09-telemetry.py`'s `UNAVAILABLE_FIELDS` gains two honestly-
named entries (`run_id`, `escalations` — see Grounding) — every consumer of
the existing keys is unaffected, since nothing removes, renames, or adds a
data key. `tools/bench.py`'s `render()` gains two report lines, printed only
when the underlying state file/telemetry log has data — the "not yet
recorded" fallback pattern every existing line already uses. `tools/test_entry_classifier.py`
gains two new assertions over data it already loads; `classify()` and
`01-entry-classifier.py` are not modified.

**Rollback:** three independent, additive commits (one per task below);
revert any one without touching the others. Nothing outside this plan reads
`SPEC_FIELD_COUNT` or the two new `UNAVAILABLE_FIELDS` entries, so reverting
Task 1 alone is clean.

**Architecture:** Each objective gets the read its own data already supports.
22's two sub-metrics are arithmetic over `build_snapshot()`'s own
`unavailable` map and `chain.fingerprint` — both already written every `Stop`.
24 aggregates the `retries.rung` field the `four-more-spec-metrics` unit
shipped hours before this plan, deduplicated to one outcome per `(slug,
attempts)` incident rather than one per turn, across every historical row in
`telemetry.jsonl` rather than just the latest. 18 replays the *same* labelled
corpus objective 8 already replays through `classify()`, at full-corpus
breadth rather than the two-stage slice `test_entry_classifier.py` currently
checks, plus a fallback-safety assertion that `01-entry-classifier.py`'s veto
mechanism degrades to an empty list rather than raising when `scope.py`
cannot be loaded.

**Tech stack and constraints:** Python 3, stdlib only (`json`, `pathlib`,
`collections`), matching every existing tool and hook in this repository.

## Grounding

- `tools/bench.py:159-171` (`skill_body_cost()`, read in full — corrected
  citation; a prior read of this plan mis-cited `total_tool_calls()`'s range
  as this function's) is the pattern every new report function mirrors: read
  a state file, return zeros with a documented "not yet recorded" meaning on
  `(OSError, ValueError)`, never raise.
- `09-telemetry.py:80-96` (`UNAVAILABLE_FIELDS`, read in full post this
  session's edits) currently names exactly **11** structurally-unavailable
  fields. Two Notion §21 fields are named in
  `docs/research/2026-08-20-notion-objectives-audit.md`'s Gap C quote but
  **currently appear in neither** the snapshot's own keys nor
  `UNAVAILABLE_FIELDS`: `run_id` (never added — this repo's telemetry has no
  per-user-task run boundary; every row is `session-cumulative`, appended
  every `Stop`, which is a different unit than the target's "one run") and
  `escalations` (the `four-more-spec-metrics` unit removed it from
  `UNAVAILABLE_FIELDS` when it added the `retries` field, but `retries` folds
  `rung`'s block/retreat outcomes in as *sub-values*, never surfaced it as its
  own key either). **Independent review caught this**: a coverage ratio of
  `(21 - len(unavailable)) / 21` silently counts an absent-and-unnamed field
  as *covered*, which is worse than the un-instrumented state this plan
  exists to fix — an uncounted gap masquerading as a good score. Task 1 adds
  both to `UNAVAILABLE_FIELDS` with honest reasons, rather than fabricating a
  `run_id` value whose only purpose would be to make the ratio look complete
  (a prior draft of this plan did exactly that with `uuid.uuid4().hex` per
  row; dropped — a random ID with no correlation use is exactly the kind of
  number that looks quantitative and proves nothing, the failure mode this
  whole unit exists to avoid).
- **Correction to the spec's clause (b) for objective 18.** The spec proposed
  asserting "agreement" between `01-entry-classifier.py` and `tools/scope.py`
  "where both classifiers fire on the same input." Reading `tools/scope.py`
  (`--help`, confirmed) shows it classifies a **git diff or a plan's declared
  file paths** (`small`/`major`/`undetermined`), never raw prompt text — there
  is no shared input space to compare two verdicts on. What `01-entry-classifier.py`'s
  own docstring at line 380-387 actually claims is narrower and checkable:
  `classify()` reads `scope.py`'s `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS`
  lists as *data*, cached at module load via `_load()`/`_control_or_sensitive_patterns()`
  (lines 331-355 — corrected names; a prior draft of this plan called this
  `_get()`, which does not exist). An earlier draft of Task 3 proposed
  comparing this cached list against a freshly-read `scope.py` — a "drift
  check" that can never go red, since both sides read the same source at
  test time. **Independent review caught this**: the check must instead
  prove the *fallback path* is safe, by forcing `_load()` to fail and
  asserting the veto degrades to an empty list rather than an unhandled
  exception or a silently-stale cache.
- `python tools/memory.py --paths tools/bench.py .claude/hooks/post-run/09-telemetry.py .claude/hooks/user-prompt/01-entry-classifier.py tools/test_entry_classifier.py tools/scope.py docs/objectives.md`
  → 30 entries, all directory-level (`MEMORY.md`'s `.claude/` pointers,
  `ISSUES.md` and `decisions/` naming the containing directory only) —
  nothing file-specific contradicts this plan.

## File map

- Modify: `.claude/hooks/post-run/09-telemetry.py` — add `run_id` and
  `escalations` to `UNAVAILABLE_FIELDS` with honest reasons; add
  `SPEC_FIELD_COUNT` constant.
- Modify: `tools/bench.py` — add `schema_coverage()`, `local_repair_ratio()`;
  two new lines in `render()`.
- Create: `tools/test_bench.py` — regression cases for both new functions,
  each with a seeded-violation proof.
- Modify: `.claude/project-checks.json` — register `python tools/test_bench.py`
  in the `test` list; add a `test_map` entry for `tools/bench.py` and
  `.claude/hooks/post-run/09-telemetry.py` pointing at it, so `--scoped`
  resolves rather than falling back to the full tier on every future change
  to either.
- Modify: `tools/test_entry_classifier.py` — full-corpus route-presence check
  (strengthened per review — see Task 3) and a fallback-safety check for the
  `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS` veto cache.
- Modify: `docs/objectives.md` — instrument table gains rows for 18, 22, 24;
  closing sentence's uninstrumented range re-split to exclude 18.

## Progress
- [x] Task 1 — Objective 22: schema coverage + trace completeness. `python
  tools/test_bench.py` exits 0, all 5 cases including the 2 seeded-violation
  ones; `python tools/bench.py` prints a real `38%` against 8/21 populated
  fields; full tier `PASS: 55 check(s) green` (found and fixed a real
  README.md suite-count drift, 44 -> 45, caught by the same run).
- [ ] Task 2 — Objective 24: local-repair ratio
- [ ] Task 3 — Objective 18: route-presence + fallback-safety check, docs update

## Tasks

### Task 1: Objective 22 — schema coverage + trace completeness
**Purpose:** a re-runnable number for "every meaningful decision, change,
verification result and failure traceable" — today this is graded once, by
reading `UNAVAILABLE_FIELDS` and trusting it stayed accurate.
**Files:**
- Modify: `.claude/hooks/post-run/09-telemetry.py` — add two entries to
  `UNAVAILABLE_FIELDS`: `"run_id": "this repo's telemetry has no per-user-
  task run boundary -- every row is session-cumulative, appended every Stop,
  a different unit than the target's 'one run'"` and `"escalations": "folded
  into retries.rung's block/retreat outcomes -- no separate counter; see
  objective 24's local_repair_ratio()"`. Add module-level `SPEC_FIELD_COUNT
  = 21  # Notion spec SS21's own named field count -- see Gap C,
  docs/research/2026-08-20-notion-objectives-audit.md` directly above
  `UNAVAILABLE_FIELDS`, with a comment listing the 21 field names for a
  future reader without re-deriving them from the audit doc.
- Modify: `tools/bench.py` — new `schema_coverage() -> tuple[float | None,
  list[str], bool]` returning `(coverage_ratio, missing_field_names,
  trace_complete)`. Reads the **last line** of
  `.claude/hooks/state/telemetry.jsonl` (mirror `session_calls()`'s
  try/except `(OSError, ValueError, IndexError)` -> `(None, [], False)`
  shape for "no data yet"). `coverage_ratio = (SPEC_FIELD_COUNT - len(
  row["unavailable"])) / SPEC_FIELD_COUNT` — import `SPEC_FIELD_COUNT` from
  the telemetry module via the same `_load_module`-style pattern already
  used elsewhere in this repo (do not hardcode `21` a second time in
  `bench.py`; one place owns the count, so the two `run_id`/`escalations`
  entries this task adds are reflected in every future read without a second
  edit). `missing_field_names = list(row["unavailable"].keys())`.
  `trace_complete = bool(row.get("chain", {}).get("fingerprint"))` —
  fingerprint, not slug: slug is legitimately `None` for a turn with no
  active plan, fingerprint is always computable.
- Modify: `tools/bench.py:render()` — new block after the existing
  `skill_body_cost()` block (`tools/bench.py:159-171`): if `coverage_ratio
  is None`, print "not yet recorded" (matching the existing convention);
  else print the ratio as a percentage, the missing field names, and the
  trace-completeness boolean.
- Test: `tools/test_bench.py` (new) — write a synthetic `telemetry.jsonl`
  fixture (tempfile, one JSON line) with a known `unavailable` map size and
  assert `schema_coverage()` computes the exact expected ratio against the
  real, current `SPEC_FIELD_COUNT` (21) — not a hardcoded local recompute of
  the same number, which would defeat the point of Task 1's single-owner
  fix; a second fixture with `chain.fingerprint` present vs. absent asserts
  `trace_complete` flips correctly; a missing/unreadable file case asserts
  the `(None, [], False)` fallback.
**Dependencies:** none.
**Implementation notes:** `SPEC_FIELD_COUNT` must live in `09-telemetry.py`,
not be re-declared in `bench.py` — two constants naming the same number is
exactly the "duplicate knowledge, paraphrased" class `no-slop` flags. Loading
it: mirror the existing `_load_module()` pattern this repo already uses
between `tools/chain.py` and `tools/loop.py` (import via
`importlib.util.spec_from_file_location`, with the `assert spec is not None`
guard this repo's `mypy.ini` already requires everywhere else this pattern
appears). **Do not add a fabricated `run_id` value to the snapshot.** An
earlier draft of this task did (`uuid.uuid4().hex` per row); independent
review correctly flagged it as a number with no correlation use, added only
to inflate the coverage ratio — exactly the "invented proxy that merely
looks quantitative" this whole unit exists to avoid. Naming the honest gap
in `UNAVAILABLE_FIELDS` is the correct fix, matching how `api_call_count`/
`latency`/`retries` were named before they were real instruments.
**Rollback:** revert the commit; the two new `UNAVAILABLE_FIELDS` entries
and `SPEC_FIELD_COUNT` disappear; `bench.py`'s report loses two lines.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_bench.py`
- Expect: exit 0, including both seeded-violation cases (a fixture with 3 of
  21 fields unavailable must report exactly `18/21`, not a rounded or
  off-by-one value; a fixture with no `chain.fingerprint` must report
  `trace_complete: False`, never silently `True`).
**Done when:** `python tools/bench.py` prints a real schema-coverage
percentage and trace-completeness boolean sourced from the actual
`telemetry.jsonl` on disk, computed against a field list that names every
one of the 21 spec fields somewhere (present or `unavailable`), with none
silently missing from both.

### Task 2: Objective 24 — local-repair ratio
**Purpose:** a re-runnable number for "detect, diagnose locally, repair when
safe... escalate only when current capability is insufficient" — the spec's
own words map directly onto `tools/loop.py:rung()`'s ladder, already
surfaced into every telemetry row's `retries.rung` field by the
`four-more-spec-metrics` unit.
**Files:**
- Modify: `tools/bench.py` — new `local_repair_ratio() -> tuple[float | None,
  dict[str, int]]` returning `(ratio, counts_by_rung)`. Reads **every** line
  of `telemetry.jsonl` (not just the last, unlike Task 1's function — this
  metric is a session-to-date aggregate). **Deduplicated by incident, not by
  turn** — independent review caught that `telemetry.jsonl` appends one row
  per `Stop` (every turn), so counting rows directly turn-weights the ratio:
  one incident that takes 20 turns to resolve would outweigh 19 incidents
  resolved in one turn each. Build `incidents: dict[tuple[str | None, int],
  str] = {}` keyed on `(row.get("chain", {}).get("slug"),
  row.get("retries", {}).get("attempts"))`; for each row where
  `row.get("retries", {}).get("rung")` is not `None`, set
  `incidents[key] = rung` (last-seen wins — the most recent row for a given
  `(slug, attempts)` pair carries that attempt's current verdict). Then
  `counts = Counter(incidents.values())`; `ratio = (counts["repair"] +
  counts["restore"]) / sum(counts.values())` when `incidents` is non-empty,
  else `None`.
- Modify: `tools/bench.py:render()` — one line: if `ratio is None`, "not yet
  recorded — no turn has entered the repair ladder this session"; else the
  percentage plus the full `counts_by_rung` breakdown (so `block`/`retreat`
  counts are visible alongside, per the spec's own instruction — a high
  ratio hides an even worse block/retreat count if only the ratio prints).
- Test: `tools/test_bench.py` — a synthetic multi-line `telemetry.jsonl`
  fixture with **one incident spanning multiple rows** (same `(slug,
  attempts)`, rung changing across rows as the incident progresses) asserts
  it counts as ONE outcome (the last rung seen), not one per row — this is
  the specific regression case for the turn-vs-incident bug independent
  review found; a second fixture mixes several distinct `(slug, attempts)`
  incidents plus `None`-rung rows (skipped) and rows with no `retries` key
  at all (must not raise) and asserts the exact expected ratio and counts;
  a fixture where every incident's rung is `block` asserts `ratio == 0.0` —
  the seeded violation this metric must be capable of reporting, not
  silently treating as healthy.
**Dependencies:** 1 (shares `tools/bench.py` and `tools/test_bench.py` —
serializing avoids two agents editing the same two files).
**Implementation notes:** Do not conflate this with Task 1's `schema_coverage()`
— different read scope (last line vs. every line) and different file
(`retries.rung` vs. `unavailable`). Record the caveat from the spec verbatim
as a code comment above `local_repair_ratio()`: a low ratio is not
automatically bad — objective 1 (minimal human interference) and objective
24 pull against each other at the margin, and this function reports the
ratio, it does not judge it. Also comment the incident-key choice: `slug`
alone is not unique across a session that worked on more than one unit, and
`attempts` alone is not unique across units that both reached the same
attempt count — the pair is the actual identity of "one thing the ladder
was asked to fix."
**Rollback:** revert the commit; `bench.py` loses the one new report line.
**Preconditions:** Task 1 landed (shared files).
**Verification:**
- Run: `python tools/test_bench.py`
- Expect: exit 0, including the multi-row-single-incident case (ratio
  reflects ONE outcome, not N) and the all-`block` seeded-violation case
  (`ratio == 0.0`, `counts["block"]` reported correctly).
**Done when:** `python tools/bench.py` prints a real local-repair ratio and
per-rung breakdown, weighted by incident rather than by turn, sourced from
the actual `telemetry.jsonl` history, with an honest "not yet recorded" when
no turn has entered the ladder.

### Task 3: Objective 18 — route-presence + fallback-safety check, docs update
**Purpose:** a re-runnable number for "detect maturity, risk and state, then
choose the workflow rather than forcing every project through one process" —
today only two of `classify()`'s five possible outputs are checked against
the corpus, and nothing asserts the classifier's control/sensitive-path veto
fails safe (empty, not silently permissive or crashing) when `scope.py`
cannot be loaded.
**Files:**
- Modify: `tools/test_entry_classifier.py` — new check function replaying
  **every** query in every skill's list in `docs/evals/trigger-queries.json`
  (217 queries across 14 skills, confirmed by direct replay this session —
  ignoring `should_trigger`/`entry` labels, since this check is about the
  classifier's own output shape, not accuracy against a label) through
  `classify()`. Collects a `collections.Counter` of returned keys. Measured
  this session against the real corpus: `{None: 184, 'entry-unframed': 13,
  'entry-open': 12, 'entry-small': 4, 'entry-direct': 4}`. **Assert
  `entry-small` and `entry-direct` both appear at least once** — not a bare
  ">1 distinct key" count. Independent review caught that the existing
  per-stage checks at `tools/test_entry_classifier.py:128-181` already pin
  `entry-open`, `entry-unframed`, and `None` corpus-wide, so a ">1 distinct"
  assertion could never go red — it would already be satisfied by tests
  that exist today. Asserting the two SPECIFIC keys nothing currently
  checks is the version that can actually fail — and confirmed reachable
  (4 occurrences each), not an assertion locked in against an empty set.
  Prints the full distribution either way.
- Modify: `tools/test_entry_classifier.py` — second new check, a **fallback-
  safety** check for `_control_or_sensitive_patterns()`
  (`01-entry-classifier.py:346-355`), not a same-source comparison.
  Independent review caught that comparing the classifier's cached veto list
  against a freshly-read `scope.py` can never fail — both sides load the
  same file at test time, so they are definitionally equal. What is
  actually checkable is the fallback path: import the entry-classifier hook
  module, reset its module-level cache
  (`hook_module._CONTROL_OR_SENSITIVE_PATTERNS = None`), monkeypatch
  `hook_module._load` to `lambda rel, name: None` (simulating `tools/scope.py`
  failing to import), call `_control_or_sensitive_patterns()`, and assert it
  returns `[]` rather than raising — `getattr(None, "CONTROL_PATTERNS", [])`
  is the actual code path this exercises. Restore the real `_load` and reset
  the cache to `None` again afterward (in a `finally`), so later real calls
  in the same test process re-load correctly. **Separately**, in the normal
  (unstubbed) path, assert `_control_or_sensitive_patterns()` returns a
  **non-empty** list — confirming the veto mechanism actually reflects
  `scope.py`'s real, current patterns rather than a hardcoded stub, which is
  the positive half of the same claim.
- Modify: `docs/objectives.md` — instrument table gains three rows:
  - `18 | tools/test_entry_classifier.py's full-corpus route-presence check (entry-small/entry-direct) + _control_or_sensitive_patterns() fallback-safety check`
  - `22 | tools/bench.py's schema_coverage() (09-telemetry.py's own unavailable map + chain.fingerprint)`
  - `24 | tools/bench.py's local_repair_ratio() (incident-deduplicated aggregate over telemetry.jsonl's retries.rung history)`
  Also re-split the closing sentence's uninstrumented-objectives range —
  currently written as a contiguous "15-20" — into `15-17, 19-20` now that
  18 is instrumented and the other four in that span are not.
**Dependencies:** 1, 2 (the docs table cites both tasks' instruments; no
shared code file with either, ordered last so the table is written once,
correctly, rather than incrementally).
**Implementation notes:** Do NOT attempt to compare `classify()`'s verdict
against `tools/scope.py`'s own CLI classification directly — see the
Grounding section above; `scope.py` classifies diffs/plan paths, not prompt
text, and there is no shared input space. Do NOT write the second check as a
same-moment comparison of two fresh reads of the same file — see this
task's own Files bullet above; that assertion cannot fail by construction.
The fallback-safety check is the version that can.
**Rollback:** revert the commit; `test_entry_classifier.py` loses the two new
checks, `docs/objectives.md`'s table reverts to naming 18/22/24 as
uninstrumented.
**Preconditions:** Tasks 1 and 2 landed.
**Verification:**
- Run: `python tools/test_entry_classifier.py`
- Expect: exit 0, including both new checks (`entry-small`/`entry-direct`
  both present; the fallback-safety check's stubbed path returns `[]` and
  its unstubbed path returns non-empty). Prove the route-presence check can
  fail: temporarily change the assertion to require a key that genuinely
  never appears in the corpus (e.g. a nonexistent `entry-bogus`), confirm it
  goes red with a clear message, then revert. Prove the fallback-safety
  check can fail: temporarily skip the `_load` stub (call
  `_control_or_sensitive_patterns()` unstubbed but assert `== []` anyway),
  confirm it goes red, then revert — quote all runs.
**Done when:** `python tools/test_entry_classifier.py` reports the real
route-distribution across the whole corpus, `entry-small` and `entry-direct`
are both confirmed reachable, and the fallback-safety check has been proven
capable of failing on both its stubbed and unstubbed assertions, not just
asserted to pass.

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — every task's Verification proves its check can fail
  before trusting it (seeded violations for Tasks 1/2, a live route-presence
  and fallback-safety failure proof for Task 3)
- [x] III Smallest change — no existing hook, gate, or field is modified;
  each task adds new functions/files beside existing ones
- [x] IV Reversibility — three independent, additive commits, each named
  with its own rollback
- [x] V No silent degradation — every "no data yet" path reports an honest
  fallback (`None`/"not yet recorded"), never a fabricated zero presented as
  a real measurement
- [x] VI Mechanism — the objective-18 fallback-safety check exists specifically because
  a claim in `01-entry-classifier.py`'s own docstring needed a test proving
  it, not just prose asserting it
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why

- **Clusters A, B, D** (the other 12 uninstrumented objectives). Each is its
  own future unit, per `docs/specs/2026-08-21-qualitative-objective-metrics.md`'s
  own decomposition — 15 objectives across 4 different mechanisms is not one
  coherent deliverable.
- **Turning any of this plan's three checks into a release-blocking gate.**
  The spec's own "Report before gate" constraint: a baseline must exist
  first, in a follow-up unit.
- **The E0-E5 execution-level router and the agent-catalogue decision
  record.** Both confirmed non-blocking for this plan's three objectives in
  the spec's "Two loose threads" section — separate candidate units.
- **Re-grading objectives 1-10, and objective 2's paid eval.** Unrelated to
  this plan's three objectives; already tracked as their own items elsewhere.
