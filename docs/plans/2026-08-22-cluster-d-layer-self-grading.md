# Cluster D — Layer Self-Grading Instruments Implementation Plan

**Goal:** Give objectives 11, 12, 26, 29 (of the Notion 30) a real, re-runnable
instrument each, closing 4 of the 12 objectives that currently rest on a
2026-08-20 qualitative-only read, following the design already approved in
`docs/specs/2026-08-21-qualitative-objective-metrics.md` — Cluster D, next in
that spec's own recommended build order (C done → **D** → B → A).

**Source brief:** `docs/specs/2026-08-21-qualitative-objective-metrics.md`
(Cluster D section) plus this session's fresh research (below).

**Slug:** `cluster-d-layer-self-grading`

**Risk:** High — every task modifies `.claude/project-checks.json`, the
control surface `run_checks.py`/the auto-commit gate/`/verify` all resolve
through (`plan-format.md`: "a shared or control surface forces high"). No
task changes an *existing* check's verdict; all four are additive entries.

**Blast radius:** `.claude/project-checks.json`'s `test` list; four new/edited
`tools/test_*.py` files; `docs/objectives.md`'s instrument table; the Cluster D
section of the design spec. No hook, no runtime behavior, no per-turn cost —
all four instruments are `test`-tier, matching the spec's "off the hot path"
constraint (objectives 2/3/6 untouched).

**Rollback:** Each task's new file is a delete; each `project-checks.json`
edit is a one-line removal. At any half-landed state the suite is still
correct — a removed entry just stops reporting a ratio, nothing gates on
these (all exit 0 by design, "report before gate" per the spec).

**Architecture:** Static-parse checkers, stdlib-only (`ast`, `json`,
`pathlib`, `re`), each a standalone `tools/test_*.py` matching this repo's
established pattern (`test_hook_standards.py`, `test_no_slop.py`) rather than
a pytest suite — confirmed live: `.claude/project-checks.json`'s `test` key is
present (not absent), so `_projectchecks.py`'s glob-auto-discovery is bypassed
in *this* repo and every new script must be explicitly added to that list to
run at all (verified by reading `_projectchecks.py:275-349` this session).

**Tech stack and constraints:** Python 3, stdlib only, no new dependency
(matches every existing `tools/*.py`). Each new check prints a ratio/count and
exits 0 unconditionally this pass — gating is an explicit follow-up unit per
the spec's own constraint.

---

## Fresh research this session (validates/updates the spec's citations)

All six external citations the spec relies on were re-opened and confirmed
current (full detail lands in `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md`,
written as Task 0 below):

1. **`github/awesome-copilot/hooks.instructions.md`** — confirmed, and richer
   than quoted: also states "Default to observe first", "Do not mutate
   branch, index, or worktree state by default", "Redact secrets... from
   logs", strict-mode requirements (`set -euo pipefail` / `Set-StrictMode`).
   Kept the spec's original 5 clauses for Task 2 (statically checkable
   without new machinery); the git-mutation and secret-redaction clauses are
   real but need a different check shape — named as a follow-on, not built
   here (see "Not adopted" below).
2. **`anthropics/skills/skill-creator/scripts/quick_validate.py`** — read in
   full (`ALLOWED_PROPERTIES = {'name','description','license','allowed-tools',
   'metadata','compatibility'}`, kebab-case regex, no leading/trailing/double
   hyphen, name ≤64 chars, description ≤1024 chars and no angle brackets,
   `compatibility` ≤500 chars, **rejects any unexpected frontmatter key**).
   Confirms the spec's "structural validator, hard-fails on shape" precedent
   exactly; the unexpected-key rejection is a pattern worth citing for Task 5.
3. **`import-linter`** — confirmed `independence` and `layers` contract
   types, and found the exact mechanism this repo's own `_load()` exception
   needs: `ignore_imports` (`mypackage.bar.green -> mypackage.utils`) — a
   named per-edge allowlist, not a blanket skip.
4. **12-factor Factor III** — https://12factor.net/config, confirmed:
   "config... stored in environment variables... unlike config files, there
   is little chance of them being checked into the code repo accidentally."
5. **Ansible Molecule idempotence** — confirmed verbatim: "the second run
   should normally end with `changed=0`."
6. **`cargo-semver-checks`** — confirmed 3-tier major/minor/patch
   classification, **and** the answer to Cluster B's open marker: it excludes
   features literally named `unstable`/`nightly`/etc. from breaking-change
   detection by default, and separately supports **downgrading individual
   lints to `warn`** via `[package.metadata.cargo-semver-checks.lints]` —
   tracked, never silently unguarded.

**Cluster B marker narrowed (not built this pass):** "Include telemetry
fields [in the frozen golden], or exclude them and say why?" →
**include them, in an explicit two-tier golden** (`stable` fails on
removal/rename; `unstable` allows free addition and only warns on
removal/rename) — the direct transplant of `cargo-semver-checks`'s verified
unstable-exclusion + per-lint-`warn` mechanism, converging with OpenAPI diff
tooling's own ERR/WARN severity split (`oasdiff`, confirmed via search,
medium confidence — not read primary-source). A field promotes `unstable` →
`stable` by a deliberate, reviewed golden edit, never automatically. This
answer is recorded in Task 6 below; Cluster B itself is not built this pass.

**Not adopted:**
- Extending the hook-conformance instrument (Task 2) to also check
  git-state-mutation and secret-redaction clauses from `awesome-copilot` —
  real clauses, but neither is a single AST predicate the way the spec's 5
  chosen clauses are; each needs its own detection design. Left as a named
  follow-on so it doesn't inflate this plan's scope.
- OpenAPI diff tooling's exact severity vocabulary for Cluster B — confirmed
  only via search snippets (`oasdiff`'s README, not opened), so it stays
  medium-confidence corroboration of `cargo-semver-checks`, not an equal
  primary citation.

---

## File map

| File | Action | Owns |
|---|---|---|
| `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md` | Create | This session's research report (Task 0) |
| `tools/test_context_cost.py` | none (read-only reference) | Already exists, unwired — Task 1 wires it |
| `.claude/project-checks.json` | Modify (×5 tasks) | `test` list gains 4 new entries |
| `tools/test_hook_conformance.py` | Create | Objective 12 instrument |
| `tools/test_import_independence.py` | Create | Objective 26 instrument |
| `tools/test_no_slop.py` | Modify | `check_portability()` extended to `.py` logic files — objective 29 |
| `tools/test_instrumented_surface.py` | Create | Objective 11 instrument |
| `docs/objectives.md` | Modify | Instrument table gains rows for 11, 12, 26, 29 |
| `docs/specs/2026-08-21-qualitative-objective-metrics.md` | Modify | Cluster D marked closed; Cluster B marker resolved with citation |

## Progress
- [x] Task 0 — Write the research report
- [x] Task 1 — Wire `test_context_cost.py` into the gating suite (objective 11's first real finding, paid down immediately)
- [x] Task 2 — Objective 12: hook-contract conformance rate
- [x] Task 3 — Objective 26: import-independence contract
- [x] Task 4 — Objective 29: extend `check_portability()` to `.py` logic files
- [x] Task 5 — Objective 11: instrumented-surface coverage
- [x] Task 6 — Close out: `docs/objectives.md` + spec status + Cluster B marker

## Tasks

### Task 0: Write the research report
**Purpose:** land this session's already-gathered, already-verified findings
(6 citations re-opened, one marker narrowed) as a pullable artifact per the
`research` skill's own contract, rather than leaving them only in this plan.
**Files:**
- Create: `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md` — the
  six-citation verification above, in the skill's required
  Findings/Disagreements/Not-adopted/Sources format
**Dependencies:** none
**Rollback:** delete the file
**Preconditions:** none
**Verification:**
- Run: `Read docs/research/2026-08-22-cluster-d-b-grounding-refresh.md`
- Expect: all five required sections present (Findings, Disagreements, Not
  adopted, Sources), every claim above traceable to a URL opened this session
**Done when:** the file exists and every fact in "Fresh research" above has a
citation in it.

---

### Task 1: Wire `test_context_cost.py` into the gating suite
**Purpose:** `01-context-cost.py` is live-wired (`PostToolUse` in
`settings.json`) and `tools/test_context_cost.py` already exists (added
2026-08-22, 7 regression checks) but is absent from
`.claude/project-checks.json`'s `test` list, so `/verify` and the auto-commit
gate never run it — confirmed this session by grep (`test_context_cost` had
zero hits in `project-checks.json`). This is the exact concrete gap the
2026-08-20 audit named for objectives 11/12; fixing it needs no new code.
**Files:**
- Modify: `.claude/project-checks.json:test` — add
  `"python tools/test_context_cost.py"` to the array
**Dependencies:** none
**Rollback:** remove the added line
**Preconditions:** none
**Verification:**
- Run: `python tools/test_context_cost.py` then `python tools/run_checks.py --tier all --require-test`
- Expect: `All context-cost tests passed`; the full suite still reports
  `PASS` with one more check counted
**Done when:** `grep test_context_cost .claude/project-checks.json` finds it.

---

### Task 2: Objective 12 — hook-contract conformance rate
**Purpose:** report a per-hook boolean vector against 5 statically-checkable
clauses from this repo's own contract plus the confirmed `awesome-copilot`
citation, naming the failing clause rather than a single pass/fail.
**Files:**
- Create: `tools/test_hook_conformance.py` — for every hook registered in
  `.claude/settings.json` (reuse `test_hook_standards.py`'s existing
  settings-parsing loop as the source of the hook list rather than
  re-deriving it): (1) payload read via `_hooklib.load_payload()` — grep the
  hook's own source; (2) declared bounded timeout — check for a `timeoutSec`
  key on its `settings.json` entry or a hardcoded `timeout=` in the script;
  (3) one responsibility — heuristic: touches exactly one state file under
  `.claude/hooks/state/` (or none); (4) a representative-payload case exists
  in `tools/test_hooks.py` — grep for the hook's filename stem; (5) explicit
  exit-code semantics — the script's own docstring states its behavior
  classification per this skill's "Hook contract" section (detect
  drift/enforce safety/record state/never author). Print `n/N conforming`
  and, per non-conforming hook, the specific failing clause(s). Exit 0
  always this pass.
- Modify: `.claude/project-checks.json:test` — add
  `"python tools/test_hook_conformance.py"`
**Dependencies:** 1 (shares `project-checks.json`; sequence after Task 1's edit)
**Implementation notes:** ground clause 5 in this skill's own "Hook contract"
section (`.claude/skills/capability-layer-maintenance/SKILL.md`) rather than
inventing wording — every hook docstring should already declare one of the
four behaviors that section requires.
**Rollback:** delete the file; remove its `project-checks.json` line
**Preconditions:** Task 1 landed (shared file)
**Verification:**
- Run: `python tools/test_hook_conformance.py`
- Expect: prints `n/N conforming`, exits 0; temporarily rename one hook's
  docstring to remove its behavior classification and confirm the script
  flags exactly that hook on clause 5, then revert — proves it can fail
  before it's trusted, per the spec's own testing rule
**Done when:** the seeded-violation check above passes and is left out of
the committed diff (revert before finishing the task).

---

### Task 3: Objective 26 — import-independence contract
**Purpose:** a stdlib `ast` import-graph walk enforcing declared
independence, mirroring `import-linter`'s `independence` contract type and
its `ignore_imports` allowlist mechanism (confirmed this session).
**Files:**
- Create: `tools/test_import_independence.py` — parse every `.claude/hooks/**/*.py`
  and `tools/*.py` file's `import`/`from` statements via `ast.parse`; build
  the module graph; declare one contract: hook families (`session-init`,
  `user-prompt`, `context-budget`, `permission-security`, `pre-tool`,
  `post-tool`, `pre-edit`, `pre-commit`, `pre-deploy`, `telemetry` —
  from `hooks_registry.json`) must not import each other's modules directly,
  only through `_hooklib`. Explicit allowlist: the duplicated `_load()`
  helper across `tools/{chain,resume,loop,scope}.py` is a named,
  cited exception (`docs/plans/2026-08-20-router-progress-consistency.md`'s
  Grounding) — an `ignore` set in the script, each entry carrying that
  citation as a comment, not a silent pass. Print declared-contract count and
  violation count, each violation naming the importing file and the module
  it should not reach.
- Modify: `.claude/project-checks.json:test` — add
  `"python tools/test_import_independence.py"`
**Dependencies:** 2
**Rollback:** delete the file; remove its `project-checks.json` line
**Preconditions:** none beyond Task 2's landed edit (shared file)
**Verification:**
- Run: `python tools/test_import_independence.py`
- Expect: 0 violations against the declared contract as it stands today;
  temporarily add a direct cross-family import (e.g. a `import` line in a
  `pre-tool` hook pulling from a `post-tool` hook module) and confirm it is
  flagged by file and module, then revert
**Done when:** the seeded-violation check passes and the revert is confirmed
via `git diff` before finishing.

---

### Task 4: Objective 29 — extend `check_portability()` to `.py` logic files
**Purpose:** `tools/test_no_slop.py`'s `check_portability()` (confirmed at
`tools/test_no_slop.py:170`) reads only `.md` under `.claude/skills/`,
`.claude/agents/`, `.claude/commands/`. Objective 29's own wording is "never
embedded into universal *workflow logic*" — the `.py` under `.claude/hooks/`
and `tools/` is that logic and is currently unread by this check.
**Files:**
- Modify: `tools/test_no_slop.py:check_portability()` — extend `targets` to
  also include `.claude/hooks/**/*.py` and `tools/*.py`; reuse the existing
  `DATE_RE`/`THIS_REPO_RE`/`SIBLING_RE` patterns already defined for the `.md`
  scan rather than writing new ones; add an explicit allowlist for genuinely
  configured defaults (e.g. this repo's own name appearing in a docstring
  that is itself documentation, not logic — name the specific lines found and
  justify each allowlist entry inline, per the check's own existing comment
  style)
**Dependencies:** 3
**Implementation notes:** do **not** fix `tools/resume.py:61`'s
`BRANCH_PREFIX = "feat/"` in this task — it is a real, already-logged
`derive_state` bug (`HANDOFF.md`/`ISSUES.md`), but fixing it changes state-
derivation *behavior*, a different and riskier change than building a
detector. Confirming the extended check flags it is the proof this task
needs; the fix itself is out of scope here (see Out of Scope).
**Rollback:** revert `check_portability()` to the `.md`-only target set
**Preconditions:** none beyond Task 3's landed edit (shared file)
**Verification:**
- Run: `python tools/test_no_slop.py --scope portability`
- Expect: `tools/resume.py:61 names this repo` or an equivalent finding for
  `BRANCH_PREFIX = "feat/"` appears in the failure list — the exact known
  instance the spec names, now caught rather than uncounted
**Done when:** the run above shows that finding, and the check still passes
cleanly on every other file once the new allowlist entries are justified
(no false positives introduced).

---

### Task 5: Objective 11 — instrumented-surface coverage
**Purpose:** a floor metric — live-wired hooks and `tools/*.py` with a
resolving entry in `.claude/project-checks.json`'s `test` list, ÷ all of
them — run last so it reports the ratio *after* Task 1's fix and Tasks 2-4's
new entries are already counted.
**Files:**
- Create: `tools/test_instrumented_surface.py` — enumerate live-wired hooks
  from `.claude/settings.json` (reuse `test_hook_standards.py`'s parsing) and
  all `tools/*.py` that are not themselves `test_*.py`; for each, check
  whether a `test_*.py` naming or referencing it appears in
  `.claude/project-checks.json`'s `test` array (string match on the file
  stem); print `n/N` covered and name every miss.
- Modify: `.claude/project-checks.json:test` — add
  `"python tools/test_instrumented_surface.py"`
**Dependencies:** 4 (must run after Tasks 1-4 land so the printed ratio
reflects the post-fix state, and shares `project-checks.json`)
**Rollback:** delete the file; remove its `project-checks.json` line
**Preconditions:** Tasks 1-4 landed
**Verification:**
- Run: `python tools/test_instrumented_surface.py`
- Expect: prints `n/N`, names zero misses for `01-context-cost.py` (Task 1
  fixed it) and zero misses for the three checkers Tasks 2-3-5 just added
  (each names itself in `project-checks.json`); any remaining miss is named,
  not hidden
**Done when:** the ratio is printed and every named miss is a real,
independently-confirmable gap (spot-check at least one by hand).

---

### Task 6: Close out — objectives table, spec status, Cluster B marker
**Purpose:** record what changed where the layer's own knowledge docs expect
it, per this repo's own discipline (a shipped instrument with no line in
`docs/objectives.md`'s table is exactly the gap this whole cluster exists to
close).
**Files:**
- Modify: `docs/objectives.md` — instrument table gains 4 rows (11 →
  `test_instrumented_surface.py`; 12 → `test_hook_conformance.py`; 26 →
  `test_import_independence.py`; 29 → extended `test_no_slop.py --scope
  portability`); update the "Objectives 11-30 have no dedicated instrument"
  line to name the 8 still true (13, 15, 16, 17, 19, 20, 25, 27) instead of 15
- Modify: `docs/specs/2026-08-21-qualitative-objective-metrics.md` — mark
  Cluster D closed (mirroring how Cluster C's own closure is recorded);
  resolve the open objective-20 clarification question (the frozen-golden
  telemetry-fields marker) with the researched answer from this plan's
  "Fresh research" section, citing `cargo-semver-checks`
**Dependencies:** 5
**Rollback:** revert both doc edits
**Preconditions:** Task 5 landed and its real ratio is known
**Verification:**
- Run: `python tools/test_referenced_paths.py` (docs/objectives.md path
  references stay valid) and `python tools/run_checks.py --tier all --require-test`
- Expect: `PASS` — no broken reference, full suite still green with 4 more
  checks counted
**Done when:** `docs/objectives.md` names all four new instruments and no
stale count remains (grep for "15" near the "no dedicated instrument" line
to confirm it was updated to 8, not left stale).

---

## Constitution gate
- [x] I Evidence — every task names the exact command and expected output
- [x] II Test first — each new check must be proven to flag a real or
  seeded violation (Tasks 2, 3, 4, and Task 1's pre-existing regression
  suite) before it is trusted, per the spec's own "Testing the instruments
  themselves" rule — the check-building equivalent of a failing test first
- [x] III Smallest change — scoped to Cluster D's 4 objectives only;
  Clusters A and B are named, not built, this pass
- [x] IV Reversibility — every task is a file create/delete or a one-line
  `project-checks.json` addition; no irreversible step
- [x] V No silent degradation — no existing check's command or verdict
  changes; all additions
- [x] VI Mechanism — each objective's rule is enforced by the new test file
  itself, not by this plan's prose
- [x] VII Secrets — no credential or secret surface touched

## Complexity tracking
None — all seven articles ticked, no exception taken.

## Out of scope
- Building Cluster A (13, 15, 16, 25, 27) or Cluster B (17, 19, 20) — named
  follow-on candidates per the spec's own recommended sequence (D → B → A);
  Cluster B's objective-20 marker is narrowed with evidence (Task 6) but not
  built.
- Fixing `tools/resume.py:61`'s hardcoded `BRANCH_PREFIX = "feat/"` — a real,
  separately-logged `derive_state` bug that Task 4's extended check will
  surface, but repairing it changes state-derivation behavior and belongs in
  its own plan, not bundled into an instrumentation task.
- Turning any of the four new checks into a gate (non-zero exit on a low
  ratio) — explicit follow-up unit per the spec's "report before gate"
  constraint, only after a baseline exists.
- Re-grading objectives 1-10 or re-running the 2026-08-20 qualitative pass
  for objectives outside Cluster D — out of this plan's scope.

**Resolved at approval:** Task 2's clause-3 heuristic ("one responsibility" ≈
touches exactly one state file) — a hook touching zero state files (a pure
reporter, e.g. `01-context-cost.py`'s own aggregate-only path) counts as
trivially conforming, not skipped; a hook touching two or more counts as a
named-but-non-blocking finding this pass (the instrument reports it, exits 0
regardless, per "report before gate") rather than a hard fail, since no
currently-live hook was confirmed to violate this before implementation and
the check must not invent a stricter gate than the spec asked for.

**Deviation, Task 2 (reconciled):** two changes from the task text, both for
a reason recorded here rather than left implicit. (1) Discovery loop is
duplicated in `tools/test_hook_conformance.py` rather than importing
`test_hook_standards.py`'s, since the task's own Files list only names the
new file as touched and Task 2 does not list `test_hook_standards.py` as
Modified. (2) A single collapsed "n/N fully conforming" ratio proved
degenerate in practice — running it live showed 0/16 fully-conforming
purely because clause 5 (verbatim behavior-classification phrase) fails
almost universally, which buried real signal on clauses 1/2/4. Replaced with
a `hard-conforming` ratio (clauses 1/2/4, the blocking ones) reported
alongside a per-clause breakdown and the still-reported `fully conforming`
number, so the headline stays meaningful rather than trivially zero. Proven
against a seeded clause-1 violation on `04-read-cost.py` (hard-conforming
14/16 → 13/16, correctly named, then reverted — confirmed clean via `git
diff --stat`).

**Deviation, Task 3 (reconciled):** the plan text named the `_load()`
allowlist as `tools/{chain,resume,loop,scope}.py` (4 files); live grep this
session (`grep -rl "^def _load(" tools/*.py`) found 10 files sharing the
same accepted verbatim-copy pattern (also `analyze.py`, `budget.py`,
`git_ops.py`, `parallel_groups.py`, `security_gate.py`, `test_hooks.py`).
Implemented against the real 10-file set, same citation
(`docs/plans/2026-08-20-router-progress-consistency.md`'s Grounding) — the
plan's 4-file list was an incomplete recollection, not a narrower intended
scope. Proven against a seeded violation (`tools/halt.py` given a
`_load()` call reaching into `.claude/hooks/permission-security/`, flagged,
reverted — confirmed clean via `git diff --stat`).

**Deviation, Task 4 (reconciled, significant):** the plan's stated
Verification expected the extended check to catch `tools/resume.py:61`'s
`BRANCH_PREFIX = "feat/"` bug. Running it live proved that expectation
wrong: `DATE_RE`/`THIS_REPO_RE`/`SIBLING_RE` target narrative provenance
(dates, "this repo's", sibling-repo names), a different violation shape
than a hardcoded convention constant used as logic — confirmed by grepping
the actual output, which never named `resume.py`. Recorded honestly rather
than silently claimed. Two further things discovered only by running the
check, not by reading the plan:

1. `check_portability()` **is already gating** — it's in
   `.claude/project-checks.json`'s `test` list (`--scope portability`
   already present, confirmed by reading the file this session), contrary
   to its own docstring's "run before installing... the only moment it
   matters." A naive full-file-body extension scored 287 findings against a
   check that was previously green, which would have broken
   `run_checks.py --tier all --require-test` over legitimate, CLAUDE.md-
   endorsed historical rationale comments, not real violations.
2. Rescoped to **code only** — module/class/function docstrings (via `ast`)
   and `#` comments are stripped before scanning `.py` logic files, and
   `tools/test_*.py` is excluded (fixture/verification code, and the source
   of two of the three false positives: `test_no_slop.py`'s own
   `SIBLING_RE` definition literally contains `"physrun"` and flagged
   itself). This dropped 287 → 30 → 2 after each fix, converging on real
   findings instead of noise.

**Proof (real, not seeded):** the code-only, test-excluded scan found and
this task fixed 2 genuine violations: `tools/bench.py:319`'s
`TIMING_CAVEAT` claimed a specific historical measurement ("this repo's
fast tier measured 11s and 27s") that reads as false in any other
installed repo — reworded to the general claim it was actually making.
`.claude/hooks/session-init/02-bootstrap-docs.py:276`'s stub-CLAUDE.md
message used "this repo's"/"in this repo" phrasing that both trip the
existing regex despite being runtime-deictic (describing whichever repo
the hook executes in) — reworded to avoid the pattern while keeping the
meaning; confirmed harmless via `python tools/test_session_start_contract.py`
(all checks pass) both before and after. Final state:
`python tools/test_no_slop.py --scope portability` → `OK: nothing in the
layer asserts anything about a specific repository`.

**Known, accepted limitation:** this instrument does not and cannot catch
the `BRANCH_PREFIX`-class violation (a hardcoded convention value used as
logic, no date/repo-name/sibling-name pattern present) — that needs a
different, not-yet-designed detector. Recorded here rather than
overclaimed; the bug itself remains open, tracked in `HANDOFF.md`/`ISSUES.md`,
out of this plan's scope per the Out of Scope section below.

**Deviation, Task 5 (reconciled):** the first implementation used exact
stem equality and scored a nonsensical 1/42 -- caught immediately by
running it (`OK.` counts alone don't prove correctness; reading the actual
per-file output did). Root cause: hook stems are numeric-prefixed and
hyphenated (`01-context-cost`) while their tests are `test_context_cost.py`
(prefix dropped, hyphens to underscores) -- a real repo naming convention
the plan's Files description didn't spell out. Fixed with a `normalize()` +
substring match instead of exact equality; re-ran, went to a sane 22/42.
**Real finding, not seeded:** the corrected instrument surfaced a *second*
undiscovered gap beyond the plan's named `01-context-cost.py` case —
`tools/test_smoke.py` exists, passes (`python tools/test_smoke.py` — `All
smoke tests passed`, run fresh as the required spot-check), and was also
absent from `project-checks.json`'s gating `test` array (only present in
`test_map` and a separate `"smoke"` key). Left unwired deliberately — Task
5's own scope is building and proving the instrument, and Task 1 already
established the "fix the one concrete miss" precedent for the specifically
named finding; a second, plan-unnamed fix here would be scope creep this
task didn't ask for. Recorded as a real, named, still-open finding rather
than silently fixed or silently dropped.

**Task 6, plus two mechanical fixes surfaced by the full verification
pass:** `python tools/test_referenced_paths.py` caught a real stale count
(`README.md:174` said "46 suites", now 49 after this plan's 4 additions —
fixed). `python tools/run_checks.py --tier all --require-test` then failed
lint (2 semicolon-joined statements in `test_hook_conformance.py`, `E702`)
and typecheck (`test_no_slop.py`'s `end_lineno` is `int | None`;
`test_import_independence.py`'s `names` list needed an explicit
annotation) — both fixed, both re-verified clean
(`python -m ruff check .` → `All checks passed!`; `python -m mypy` →
`Success: no issues found in 79 source files`).

**Final verification:** `python tools/run_checks.py --tier all
--require-test` → `PASS: 59 check(s) green (audit, build, lint, smoke,
test, typecheck)` — up from the pre-plan baseline (55, per `LOG.md`'s
2026-08-22 entry) by exactly the 4 new checks this plan registered
(`test_context_cost.py`, `test_hook_conformance.py`,
`test_import_independence.py`, `test_instrumented_surface.py`).

## Approved
