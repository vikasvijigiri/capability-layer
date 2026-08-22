# Cluster A — Target-Matrix Conformance Implementation Plan

**Goal:** Give objectives 15, 16, 25, 27 (of the Notion 30) a real,
re-runnable instrument each, closing 4 more of the 12 objectives that
currently rest on a 2026-08-20 qualitative-only read, following the design
already approved in `docs/specs/2026-08-21-qualitative-objective-metrics.md`
— Cluster A, last in that spec's own recommended build order (C done → D
done → B not yet built → **A**, built here out of the recommended order at
explicit user direction). Objective 13 (universal/generic) is already Green
via `.claude/adapters/*.json`'s `conformance` field and
`tools/test_portability_contract.py`; this plan adds no new instrument for
it, per the spec's own words ("this objective is already Green; the
instrument exists to detect regression, not to re-litigate").

**Source brief:** `docs/specs/2026-08-21-qualitative-objective-metrics.md`
(Cluster A section), resolving its one open question (fixture corpus:
checked in vs. generated at test time) in favor of **generated at test
time**, per `tools/test_install.py`'s own precedent and this repo's proven
discipline of shrinking its installable payload (1,586,874 → 1,172,851
bytes, `TASK.md`'s "Make the layer portable" entry) — checking in a
multi-stage synthetic corpus would partially undo that objective-14 win.

**Slug:** `cluster-a-target-matrix`

**Risk:** Medium — the diff touches `.claude/project-checks.json`'s `test`
list (a control surface `run_checks.py`/the auto-commit gate/`/verify` all
resolve through), but every other file is new or documentation. No task
changes an *existing* check's verdict; the one entry added is additive.

**Blast radius:** `.claude/project-checks.json`'s `test` list (one new
line); one new file, `tools/test_target_matrix.py`; `docs/objectives.md`'s
instrument table; the Cluster A section of the design spec. No hook, no
runtime behavior, no per-turn cost — the new instrument is `test`-tier only,
matching the spec's "off the hot path" constraint (objectives 2/3/6
untouched). Fixtures are built in a temp directory per run and deleted at
the end; nothing is checked in.

**Rollback:** Delete `tools/test_target_matrix.py`; remove its one line from
`.claude/project-checks.json`. At any half-landed state the suite is still
correct — the new check reports a ratio and exits 0 by design ("report
before gate", per the spec's Constraints).

**Architecture:** One static-corpus-and-conformance checker,
`tools/test_target_matrix.py`, matching this repo's established
non-pytest, standalone-script pattern (`test_install.py`, `test_recon.py`).
The fixture builder is **inline in the same file** (not a separate
`tools/fixtures.py`) — the corpus and the checks that consume it are one
unit of work, and `test_install.py`'s own `fresh_repo()` helper is the
precedent for keeping fixture construction inline rather than a shared
module. All five objectives' checks read the SAME corpus, which is the
whole reason the spec clusters them into one deliverable. Fixture
install/recon/check-resolution calls are made **in-process** (direct
function calls into `.claude/install.py`, `tools/recon.py`, and
`.claude/hooks/_projectchecks.py`, loaded the same way `test_install.py`
already loads them) rather than via `subprocess` per fixture — this is a
deliberate cost decision, recorded under Task 2's Implementation notes,
because `tools/run_checks.py --tier fast` is documented to fire a
sub-process per resolved *check*, and doing that once per fixture on top of
a fresh Python interpreter start per fixture would multiply the tier's
wall-clock cost for a repo-portability property that does not need a real
subprocess boundary to prove.

**Tech stack and constraints:** Python 3, stdlib only, no new dependency.
The new check prints per-objective ratios/booleans and exits 0
unconditionally this pass — gating is an explicit follow-up unit per the
spec's own constraint, same as Cluster C and D.

---

## Fresh research this session

None needed — the spec's existing citations (`test_install.py`'s own
`fresh_repo()` precedent for objective 15's harness shape;
`obra/superpowers`'s `porting-to-a-new-harness.md` Definition of Done for
"support is a run that happened, not a claim", already cited for objective
13; `install.py`'s own `PYTHON_SEED`/`target_has_python()` mechanism,
already implemented, for objective 25) are sufficient and were re-read this
session directly from source rather than re-fetched. The one design
question the spec left open (checked-in vs. generated corpus) is answered
above rather than re-argued.

---

## File map

| File | Action | Owns |
|---|---|---|
| `tools/test_target_matrix.py` | Create (built across Tasks 1-5) | Objectives 15, 16, 25, 27 instruments + the shared fixture corpus |
| `.claude/project-checks.json` | Modify | `test` list gains 1 new entry; `test_map` gains 1 row |
| `docs/objectives.md` | Modify | Instrument table gains rows for 15, 16, 25, 27; explicit note that 13 needs none |
| `docs/specs/2026-08-21-qualitative-objective-metrics.md` | Modify | Cluster A marked closed |
| `TASK.md` | Modify | Active entry for this unit |
| `LOG.md` | Modify | One dated entry |

## Progress
- [x] Task 1 — Build the fixture corpus (5 stages + 1 non-Python stack)
- [x] Task 2 — Objective 15: stage-fixture pass rate
- [x] Task 3 — Objective 16: repository-agnostic (real structure + zero check-leakage)
- [x] Task 4 — Objective 25: technology-agnostic (stack coverage)
- [x] Task 5 — Objective 27: progressively adoptable (zero-migration boolean)
- [x] Task 6 — Wire into the gating suite; close out docs

## Tasks

### Task 1: Build the fixture corpus
**Purpose:** one small, cheap, in-memory-built corpus every later task reads:
five stages named verbatim by objective 15 (greenfield, partial, legacy,
broken, undocumented) plus one non-Python/non-Node stack (a Go layout) for
objective 25. Each fixture is a handful of files, not a realistic app —
this only needs to exercise install/recon/run_checks, not run a real build.
**Files:**
- Create: `tools/test_target_matrix.py` — `_git_init()` helper (mirrors
  `test_install.py`'s `fresh_repo()`); six builder functions
  (`fixture_greenfield`, `fixture_partial`, `fixture_legacy`,
  `fixture_broken`, `fixture_undocumented`, `fixture_go`), each returning a
  `Path` inside a shared `tempfile.mkdtemp()`; a `STAGES` dict naming the
  five objective-15 stages. `fixture_broken` includes both a syntactically
  invalid `.py` file and a test that asserts `False`, so the fixture is
  broken independent of which toolchain happens to be installed on the
  machine running this suite. `fixture_partial`, `fixture_legacy`,
  `fixture_broken`, and `fixture_undocumented` each get a trivial
  `check.py` (`print("ok")`) standing in for "the target's pre-existing
  build/test command", read by Task 5.
**Dependencies:** none
**Rollback:** delete the file
**Preconditions:** none
**Verification:**
- Run: `python tools/test_target_matrix.py`
- Expect: prints `6 fixture(s) built` (or equivalent) and exits 0 — no
  assertions about install/recon/checks yet, just that every builder
  produces a real directory with a real `.git`
**Done when:** all six fixtures build without exception and each has a
`.git` directory.

---

### Task 2: Objective 15 — stage-fixture pass rate
**Purpose:** *"Stage-agnostic — correct on greenfield, partial, legacy,
broken, undocumented, active or near-release repositories."* Install, then
`recon.gather()`, then `_projectchecks.run_checks(fixture, kinds=FAST_KINDS)`
against each of the five named stages. Pass = no exception raised by any of
the three steps, and `recon.gather()` returns a non-empty facts dict (has
`root`/`stack`/`tests`/`git`/`units` keys) for every stage including the
empty greenfield one.
**Files:**
- Modify: `tools/test_target_matrix.py` — load `.claude/install.py`,
  `tools/recon.py`, `.claude/hooks/_projectchecks.py` the same way
  `test_install.py` already does (`importlib.util.spec_from_file_location`);
  for each of the 5 `STAGES`, run `inst.plan`/`inst.apply`,
  `recon.gather(fixture)`, `pc.run_checks(fixture, kinds=pc.FAST_KINDS)`
  inside a `try/except`, recording pass/fail and the exception text if any;
  print `stage-fixture pass rate: n/5` and name every failing stage.
**Dependencies:** 1
**Implementation notes:** in-process calls, not `subprocess` — see the
plan header's Architecture note on cost. `recon.gather()` and
`_projectchecks.run_checks()` are both pure Python functions taking a
`root` argument; calling them directly is what
`test_install.py:_pc.resolve_checks(_nopy, ...)` already does for the same
reason, generalised from "resolve" to the "run" it wraps.
**Rollback:** revert the file to Task 1's state
**Preconditions:** none beyond Task 1
**Verification:**
- Run: `python tools/test_target_matrix.py`
- Expect: `stage-fixture pass rate: 5/5`; temporarily make
  `fixture_broken()` raise (e.g. write to a nonexistent nested path without
  `mkdir(parents=True)`) and confirm the ratio drops to `4/5` naming
  `broken`, then revert — proves the check can fail before it is trusted
**Done when:** the seeded-failure proof above passes and `git diff` is
clean after reverting it.

---

### Task 3: Objective 16 — repository-agnostic
**Purpose:** *"Discover structure, conventions, dependencies, tooling,
architecture and constraints before assuming or changing."* Two assertions
over the same corpus: (a) `recon.gather()` reports the REAL stack per
fixture (`languages` empty for the empty greenfield stage, `["python"]` for
the four Python stages) rather than a constant; (b) zero checks resolved
for a fixture ever match a command string from THIS repository's own
`.claude/project-checks.json` `test` array — the direct test that
`_projectchecks.resolve_checks(root=...)` is actually scoped to the `root`
it is given rather than silently falling back to this repository, which is
the literal reading of the spec's "zero checks resolved from this repo's
own project-checks.json when running inside a fixture."
**Files:**
- Modify: `tools/test_target_matrix.py` — after Task 2's install/recon
  pass, assert `facts["stack"]["languages"]` per stage; separately, load
  this repo's own `test` array from `.claude/project-checks.json`,
  compute `own = set(that array)`, and for each fixture compute
  `resolved, _ = pc.resolve_checks(fixture, pc.FAST_KINDS)` and assert
  `own & {cmd for _, cmd in resolved} == set()`. Include the proof that
  this assertion has teeth: `pc.resolve_checks(ROOT, pc.FAST_KINDS)`
  (this repository resolving its own checks) MUST intersect `own`
  non-emptily — if it did not, the fixture-side assertion would be
  vacuously true and prove nothing.
**Dependencies:** 2 (shares the file; sequenced after Task 2's install
loop so recon/resolve results are already computed once, not twice)
**Rollback:** revert the file to Task 2's state
**Preconditions:** Task 2 landed
**Verification:**
- Run: `python tools/test_target_matrix.py`
- Expect: zero leaked commands across all 5 stages; the "has teeth" proof
  passes (ROOT's own resolution does intersect `own`)
**Done when:** both assertions pass and the teeth-proof is confirmed by
reading its own printed detail, not just the exit code.

---

### Task 4: Objective 25 — technology-agnostic
**Purpose:** *"Languages, frameworks, build systems, package managers,
deployment models and layouts, without hardcoded assumptions."* Closes the
audit's exact Amber wording: `install.py` seeds Python lint config only
into hosts that have Python — verified here against a real non-Python,
non-Node stack rather than asserted.
**Files:**
- Modify: `tools/test_target_matrix.py` — install into `fixture_go` the
  same way as the other stages; assert `ruff.toml` and `mypy.ini` are NOT
  created (`PYTHON_SEED` skip, already implemented in `install.py`); assert
  `recon.gather()` reports `"go"` in `facts["stack"]["languages"]`; assert
  the two "not seeded" warnings from `inst.plan()` name `ruff.toml` and
  `mypy.ini`.
**Dependencies:** 3
**Rollback:** revert the file to Task 3's state
**Preconditions:** none beyond Task 3's landed edit (shared file)
**Verification:**
- Run: `python tools/test_target_matrix.py`
- Expect: `go-stack: no Python config seeded, language=go`; temporarily add
  a stray `x.py` file to `fixture_go` before install, confirm ruff.toml/
  mypy.ini now ARE seeded (proving the assertion is live, not vacuous),
  then revert
**Done when:** the seeded-file proof above is confirmed and reverted
(`git diff` clean).

---

### Task 5: Objective 27 — progressively adoptable
**Purpose:** *"Value when dropped into an existing repository without
requiring a rewrite, reorganization or migration first."* Zero-migration
boolean: after install, (a) every file path that existed before install
still exists at the SAME relative path after (nothing moved or renamed —
deliberately narrower than objective 17's future preservation-rate
instrument in Cluster B, which will check byte-identical CONTENT; this
checks paths only, so the two clusters do not duplicate each other's
future work), and (b) the fixture's own pre-existing `check.py` command
still runs and produces byte-identical output before and after install.
**Files:**
- Modify: `tools/test_target_matrix.py` — capture each fixture's file-path
  set BEFORE `inst.apply()` runs (must happen before Task 2's install loop
  executes, so this task's snapshot logic is inserted ahead of it in the
  file, not appended after); for `fixture_partial` specifically, also
  capture `subprocess.run([sys.executable, "check.py"], cwd=fixture)`'s
  stdout before install; after install, assert the pre-install path set is
  a subset of the post-install path set, and re-run `check.py`, asserting
  identical stdout.
**Dependencies:** 4
**Rollback:** revert the file to Task 4's state
**Preconditions:** none beyond Task 4's landed edit (shared file)
**Verification:**
- Run: `python tools/test_target_matrix.py`
- Expect: `zero-migration: True` for every non-greenfield stage;
  `check.py` output unchanged; temporarily have `fixture_partial()` NOT
  write `check.py`, confirm the check reports the missing-file case
  honestly (not a silent pass), then revert
**Done when:** the pre/post output comparison is proven live (not simply
asserting `True == True`) by the revert above.

---

### Task 6: Wire into the gating suite; close out
**Purpose:** register the new check where `/verify` and the auto-commit
gate actually look, and record what changed where this layer's own
knowledge docs expect it.
**Files:**
- Modify: `.claude/project-checks.json` — add
  `"python tools/test_target_matrix.py"` to `test`; add
  `"tools/test_target_matrix.py": "python tools/test_target_matrix.py"` to
  `test_map`
- Modify: `docs/objectives.md` — instrument table gains 4 rows (15, 16, 25,
  27 → `tools/test_target_matrix.py`, one command answering all four);
  update the "Objectives ... have no dedicated instrument" line to drop 15,
  16, 25, 27 (leaving 17, 19, 20 — Cluster B, not yet built) and state
  explicitly that objective 13 needed no new row (already Green via
  `.claude/adapters/*.json` + `test_portability_contract.py`)
- Modify: `docs/specs/2026-08-21-qualitative-objective-metrics.md` — mark
  Cluster A closed, mirroring Cluster C/D's own closure notes
- Modify: `TASK.md` — Active entry for this unit
- Modify: `LOG.md` — one dated entry (~15 lines)
**Dependencies:** 5
**Rollback:** revert all doc edits; remove the `project-checks.json` lines
**Preconditions:** Task 5 landed and its real numbers are known
**Verification:**
- Run: `python tools/test_referenced_paths.py` then
  `python tools/run_checks.py --tier all --require-test`
- Expect: no broken reference; final `PASS` line quoted verbatim in the
  plan's closing note
**Done when:** `docs/objectives.md` names the new instrument for all four
objectives and no stale "no dedicated instrument" count remains.

---

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — each new check must be proven to flag a real or
  seeded failure (Tasks 2, 3, 4, 5's revert-proofs) before it is trusted,
  per the spec's own "Testing the instruments themselves" rule
- [x] III Smallest change — scoped to Cluster A's 4 objectives only (13
  needs none); Cluster B is not built this pass
- [x] IV Reversibility — every task is a file create/delete or a one-line
  `project-checks.json` addition; no irreversible step; fixtures live only
  in a temp directory, deleted at the end of every run
- [x] V No silent degradation — no existing check's command or verdict
  changes; one addition
- [x] VI Mechanism — each objective's rule is enforced by the new test
  file itself, not by this plan's prose
- [x] VII Secrets — no credential or secret surface touched

## Complexity tracking
None — all seven articles ticked, no exception taken.

## Out of scope
- Building Cluster B (17, 19, 20) — a separate, not-yet-built unit; this
  plan deliberately keeps objective 27's file-path check narrower than
  Cluster B's future content-preservation check so the two do not
  duplicate work.
- Checking the fixture corpus into the repository — resolved above in
  favor of generating it at test time, matching `test_install.py`'s
  precedent and preserving the objective-14 payload-size win.
- Turning `tools/test_target_matrix.py` into a gate (non-zero exit on a
  low ratio) — explicit follow-up unit per the spec's "report before gate"
  constraint, only after a baseline exists.
- Re-grading objectives 1-10, or re-running the 2026-08-20 qualitative pass
  for objectives outside Cluster A.
- A real Go toolchain, or compiling/running the Go fixture — the layout
  alone (`go.mod` + a package directory) is what objective 25 asks for;
  nothing here needs `go` installed on the machine running the suite.

## Deviations and findings, recorded per this repo's discipline

**Deviation, Task 2 (reconciled, cost):** the plan's first draft called
`pc.run_checks(fixture, kinds=FAST_KINDS)` — the real, executing fast tier
— for all 5 stages. Measured live: ~3.15s per Python fixture, almost all
`mypy`/`ruff` subprocess startup once `install.py` seeds `ruff.toml`/
`mypy.ini` into any fixture with real `.py` files (`target_has_python()`
fires on the fixture's own source, independent of which manifest is
present). Running that for 4 Python stages would have added ~12-13s to a
check joining the FAST tier. Rescoped: every stage still calls the cheap
`resolve_checks()` (proves no crash in detection), and only `broken` — the
stage whose whole point is to be a hard case — runs the real `run_checks()`
end to end. Net measured cost: fast tier 39.596s (49 checks, file absent)
→ 44.333s (50 checks, file present and wired), a clean before/after with
the file moved aside and restored, not a guess.

**Real bug found by the seeded-violation proof, Task 5 (significant):**
the first draft of the objective-27 zero-migration check compared
`check.py`'s stdout before and after install
(`post_check_output == pre_check_output`). Seeding the violation named in
the plan's own Verification step — deleting `check.py` from the `partial`
fixture before the "before" snapshot — proved the check WORTHLESS rather
than failing: a missing `check.py` makes `python check.py` exit nonzero
with EMPTY stdout on both the before and the after run, so two empty
strings compared equal and the check reported `PASS`. This is the same
class of false-confidence gap Cluster D's Task 5 found (a naive stem-match
scoring a nonsensical 1/42) and Task 4 found (287 false positives) —
caught only by actually running the seeded case, not by reading the check.
Fixed: `run_check_py()` now returns `(returncode, stdout)`, and the
assertion requires `returncode == 0` and the stdout to equal the known
literal `"ok"` on BOTH runs, plus a separate sanity assertion that the
pre-install baseline itself is real (`rc == 0 and output == "ok"`) before
the before/after comparison is trusted at all. Re-seeded after the fix:
correctly reports 2 named failures (the sanity check and the unchanged-
command check) instead of a silent pass. `git diff` on the real file was
never touched during the seeding — the proof ran against a monkeypatched
in-memory copy of the module, matching this repo's `test_install.py`
precedent of proving a check via a constructed violation rather than
editing and reverting the file under test.

**Real, pre-existing flake surfaced (not a regression), Task 6:** the
first `--tier all --require-test` run after wiring the new check in failed
`test_project_checks.py` with "the default pool runs checks concurrently
-- their intervals overlap -- probe intervals did not intersect" — a
timing-sensitive concurrency-probe assertion inside that suite, unrelated
to anything this plan's code does. Run standalone, `test_project_checks.py`
passed cleanly; run again as part of the full tier, the full tier passed
cleanly too. Recorded as a real, pre-existing flakiness risk in that
suite's own timing probe, made more likely to surface by this plan adding
~4.7s of extra concurrent load to an already-large thread pool — not
something this plan's own check should silently work around, and not a
defect in `tools/test_target_matrix.py` itself.

**Final verification:** `python tools/run_checks.py --tier all
--require-test` → `PASS: 56 check(s) green (audit, build, lint, smoke,
test, typecheck)` — up from the pre-plan baseline of 55 (per `TASK.md`'s
most recent completed entry) by exactly the 1 new check this plan
registered. `python -m ruff check tools/test_target_matrix.py` →
`All checks passed!`; `python -m mypy tools/test_target_matrix.py` →
`Success: no issues found in 1 source file`.

## Approved end
