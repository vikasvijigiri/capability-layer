# Cluster B — Re-run Safety Instruments Implementation Plan

**Goal:** Give objectives 17 (non-destructive integration), 19 (idempotent and
repeatable), 20 (backward-compatible where practical) a real, re-runnable
instrument each, closing 3 more of the objectives that currently rest on a
2026-08-20 qualitative-only read, following the design already approved in
`docs/specs/2026-08-21-qualitative-objective-metrics.md` -- Cluster B, next in
that spec's own recommended build order (C done -> D done -> **B** -> A), with
the one open design question (Cluster B's frozen-golden telemetry-field
marker) already resolved 2026-08-22 in that same spec file, ahead of this
unit.

**Source brief:** `docs/specs/2026-08-21-qualitative-objective-metrics.md`
(Cluster B section) plus this session's fresh research (below) -- `docs/plans/
2026-08-22-cluster-d-layer-self-grading.md` is the worked sibling pattern this
plan mirrors exactly (file shape, per-task Verification, Deviation-note
convention).

**Slug:** `cluster-b-rerun-safety`

**Risk:** High -- every task modifies `.claude/project-checks.json`, the
control surface `run_checks.py`/the auto-commit gate/`/verify` all resolve
through (`plan-format.md`: "a shared or control surface forces high"). No
task changes an *existing* check's verdict; all three are additive entries.

**Blast radius:** `.claude/project-checks.json`'s `test` list; three new
`tools/test_*.py` files; one new checked-in golden JSON under
`.claude/contracts/`; `docs/objectives.md`'s instrument table; the Cluster B
section of the design spec. No hook, no runtime behavior, no per-turn cost --
all three instruments are `test`-tier, matching the spec's "off the hot path"
constraint (objectives 2/3/6 untouched). No file any new check reads is
mutated by the check itself (every fixture lives under `tempfile.mkdtemp()`).

**Rollback:** Each task's new file is a delete; each `project-checks.json`
edit is a one-line removal. At any half-landed state the suite is still
correct -- a removed entry just stops reporting a ratio, nothing gates on
these (all exit 0 by design, "report before gate" per the spec).

**Architecture:** Static-parse-and-fixture checkers, stdlib-only (`json`,
`pathlib`, `tempfile`, `subprocess`, `importlib.util`), each a standalone
`tools/test_*.py` matching this repo's established pattern
(`test_install.py`, Cluster D's four checkers) rather than a pytest suite.
`.claude/project-checks.json`'s `test` key is present (not absent), so every
new script must be explicitly added to that list to run at all -- confirmed by
reading the file this session (same fact Cluster D's plan already recorded).

**Tech stack and constraints:** Python 3, stdlib only, no new dependency
(matches every existing `tools/*.py`). Each new check prints a ratio/count
and exits 0 unconditionally this pass -- gating is an explicit follow-up unit
per the spec's own constraint. Fixture machinery is duplicated in each new
file (`fresh_repo()`, a small `load()` shim for `.claude/install.py`) rather
than imported from `tools/test_install.py`, because that file is a top-level
script whose import executes its entire ~930-assertion suite as a side
effect -- it cannot be imported as a library. This mirrors the repo's own
already-cited, already-accepted `_load()`-duplication pattern across 10 files
(`docs/plans/2026-08-20-router-progress-consistency.md`'s Grounding, reused
verbatim by Cluster D's Task 3).

---

## Fresh research this session

**Cluster B's own open marker was resolved 2026-08-22**, ahead of this unit,
in `docs/specs/2026-08-21-qualitative-objective-metrics.md`'s "Resolved
2026-08-22" note (citing `docs/research/2026-08-22-cluster-d-b-grounding-refresh.md`):
telemetry fields join the frozen golden in an explicit two-tier split --
`stable` (removal or rename fails the check) and `unstable` (free addition;
removal or rename only warns). Direct transplant of `cargo-semver-checks`'s
verified `unstable`/`nightly` feature exclusion plus its per-lint `warn`
downgrade mechanism (`[package.metadata.cargo-semver-checks.lints]`) -- used,
not re-verified fresh this session (already primary-sourced by Cluster D's
research report).

**The stable/unstable split itself is grounded in this repo's own `LOG.md`,
not invented.** `build_snapshot()` in `.claude/hooks/telemetry/09-telemetry.py`
returns 16 top-level fields. Three were added or fundamentally reshaped in the
final 48 hours of this session's own history, per `LOG.md`'s own dated
entries read this session:

- `run_id` -- added by the `run-id-and-volatile-cd-prefix` unit (this
  branch's own parent commit, 2026-08-22).
- `execution_level` -- added 2026-08-22 06:21 ("closing the E0-E5
  execution-level gap ... now a live `{predicted, actual}` pair"), and its
  `.actual` computation was *itself* rewritten again at 2026-08-22 16:52
  (diffing against the previous telemetry row instead of raw cumulative
  counters) -- the single most recently-changed field in the schema.
- `retries` -- Cluster C's own section of the design spec calls it "the
  `retries.rung` field that shipped hours ago" (2026-08-21).

The other 13 fields (`ts`, `run_scope`, `chain`, `tools_called`,
`skills_loaded`, `task_type`, `context_read`, `agents_spawned`,
`duplicate_rate`, `api_calls`, `turn_latency_seconds`, `human_interventions`,
`unavailable`) trace to PR #21 (`fix/unified-telemetry-schema`, merged
2026-08-20 per `LOG.md`'s retroactive entry) -- the schema-consolidation
commit, two full days more settled than the three above. `unstable` = {added
or structurally rewritten since 2026-08-21}; `stable` = {present unchanged
since the 2026-08-20 consolidation}. This is the same "three added this week"
fact the spec's own marker already named -- narrowed here to the exact three
field names with the exact commit-level evidence, not re-guessed.

**Not adopted:** freezing agent (`.claude/agents/*.md`) or command
(`.claude/commands/*.md`) names into the golden. The spec's own Cluster B
section names exactly four categories as "clearly in" (skills + frontmatter
keys, hook event registrations, `capabilities.json` names,
`project-checks.json` keys) plus telemetry fields (resolved above); agents
and commands are not among them, and adding them is scope the spec did not
ask for. Left as a named follow-on rather than silently bundled in.

---

## File map

| File | Action | Owns |
|---|---|---|
| `.claude/project-checks.json` | Modify (x3 tasks) | `test` list gains 3 new entries |
| `tools/test_idempotence.py` | Create | Objective 19 instrument |
| `tools/test_preservation_rate.py` | Create | Objective 17 instrument |
| `.claude/contracts/layer-contract.golden.json` | Create | Objective 20's frozen baseline |
| `tools/test_contract_surface.py` | Create | Objective 20 instrument |
| `docs/objectives.md` | Modify | Instrument table gains rows for 17, 19, 20; stale "no instrument" line corrected |
| `docs/specs/2026-08-21-qualitative-objective-metrics.md` | Modify | Cluster B marked closed |

## Progress
- [x] Task 1 -- Objective 19: idempotence instrument (install-twice tree
      delta + decision-hook determinism)
- [x] Task 2 -- Objective 17: preservation rate over the host's own files
- [x] Task 3 -- Objective 20: contract-surface diff against a frozen golden
- [x] Task 4 -- Close out: `docs/objectives.md` + spec status

## Tasks

### Task 1: Objective 19 -- idempotence instrument
**Purpose:** "repeated execution converges without duplicating work,
corrupting artifacts or introducing inconsistency" -- proven two ways, per
the spec's own instrument: (a) install into a fixture target twice and diff
the tree at the byte level (a stronger assertion than
`test_install.py`'s existing "no create/overwrite actions on a second plan"
-- that one is a boolean over the *action list*; this one hashes every file
before and after and reports a ratio); (b) fire a curated set of stateless
decision hooks twice with an identical payload and assert the decision
(exit code + stdout) is identical both times.
**Files:**
- Create: `tools/test_idempotence.py` -- `fresh_repo()` + a `load()` shim
  duplicated from `test_install.py`'s pattern (see Architecture); installs
  the layer into a fresh fixture, snapshots `{path: sha256}` for every file,
  installs again, snapshots again, reports `unchanged/total` (expect
  1.0). Second half: reuses `tools/test_hooks.py`'s `run_hook(event,
  payload)` helper (duplicated, same reason) to fire `pre-edit`,
  `permission-security` (both the clean-file ALLOW case and the
  planted-secret DENY case, using the same runtime-assembled key
  `test_hooks.py` uses so this file does not itself become an
  uncommittable secret), and `pre-tool` (halt-guard's default ALLOW path)
  twice each against `cwd=ROOT`, and asserts run 1 and run 2 produce the
  same exit code and the same `"permissionDecision"` value where present.
- Modify: `.claude/project-checks.json:test` -- add
  `"python tools/test_idempotence.py"`
**Dependencies:** none
**Rollback:** delete the file; remove its `project-checks.json` line
**Preconditions:** none
**Verification:**
- Run: `python tools/test_idempotence.py`
- Expect: prints an install-twice ratio of `1.0` and `OK` for every
  decision-hook determinism case; exits 0
**Done when:** the ratio is printed, every hook-determinism case is named
individually (not collapsed into one boolean), and a deliberately corrupted
in-memory "second snapshot" (a synthetic dict, no filesystem mutation) is
shown to make the ratio-computing function report `<1.0` and name the
changed path, proving the arithmetic before it is trusted.

---

### Task 2: Objective 17 -- preservation rate over the host's own files
**Purpose:** "coexist with existing workflows; preserve working behavior" --
report what fraction of a target's *own* pre-existing files survive an
install byte-identical. Scoped to the host's own files, not the layer's own
payload paths: a file this layer's `install.py` itself owns (anything in
`inst.payload_files()`, e.g. `.claude/workflow.md`) is *entitled* to be
written or refreshed as part of installing/upgrading the layer -- the
guarantee objective 17 is actually about is that a host's *own* code is
never touched. `.claude/settings.json` (in `inst.MERGE`) is reported as a
distinct third bucket (merged, not preserved, not destroyed) rather than
folded into either side.
**Files:**
- Create: `tools/test_preservation_rate.py` -- builds a fixture with (a) host
  files outside every layer path (`src/app.py`, a top-level `README.md`,
  a nested `docs/notes.md`), (b) an existing `CLAUDE.md` and
  `.claude/project-checks.json` (the two `PRESERVE` entries), (c) existing
  `ruff.toml`/`mypy.ini` (the two `SEED` entries). Snapshots `{path: bytes}`
  for every file NOT in `inst.payload_files()` and not `.claude/settings.json`
  before install, installs, snapshots again, reports
  `preserved/total` (expect 1.0) with any survivor mismatch named. Also
  confirms `--dry-run` still writes nothing (single assertion, not a
  re-implementation of `test_install.py`'s existing 2-check proof of the
  same fact -- cites it rather than duplicating it).
- Modify: `.claude/project-checks.json:test` -- add
  `"python tools/test_preservation_rate.py"`
**Dependencies:** 1 (shares `project-checks.json`; sequence after Task 1's edit)
**Rollback:** delete the file; remove its `project-checks.json` line
**Preconditions:** Task 1 landed (shared file)
**Verification:**
- Run: `python tools/test_preservation_rate.py`
- Expect: prints `preserved/total = N/N (1.0)`; exits 0; a synthetic
  in-memory before/after pair with one byte flipped is shown to make the
  ratio function report the exact file and a ratio `<1.0`, proving the
  check can fail before it is trusted (per the spec's "Testing the
  instruments themselves" rule) -- no real repo file is mutated to prove
  this, only a fixture-local temp copy
**Done when:** the seeded-violation proof above passes and the real ratio
against the actual installer is `1.0`.

---

### Task 3: Objective 20 -- contract-surface diff against a frozen golden
**Purpose:** "preserve contracts, interfaces and behavior unless a
deliberate, justified breaking change is required" -- the only objective of
the fifteen the 2026-08-20 audit graded Unmeasured rather than Amber. Freeze
the layer's own public contract surface; fail on a removal or rename,
allow every addition; a deliberate break updates the golden in the same
commit, per `cargo-semver-checks`'s model (already cited and confirmed in
the design spec).
**Files:**
- Create: `.claude/contracts/layer-contract.golden.json` -- computed from the
  live tree this session (see contents below); five categories, all
  `stable` except telemetry's own two-tier split:
  - `skills.names` -- the 14 skill directory names under `.claude/skills/`
  - `skills.frontmatter_keys` -- the union of frontmatter property names in
    use across every `SKILL.md` (`allowed-tools`, `description`,
    `disable-model-invocation`, `effort`, `model`, `name` -- 6, confirmed by
    parsing all 14 files this session)
  - `hook_events` -- the 5 event names registered as keys in
    `.claude/settings.json`'s `hooks` object (`PostToolUse`, `PreToolUse`,
    `SessionStart`, `Stop`, `UserPromptSubmit`)
  - `capabilities` -- the 9 keys of `.claude/portability/capabilities.json`'s
    `capabilities` object
  - `project_checks_keys` -- the 8 non-underscore-prefixed top-level keys of
    `.claude/project-checks.json` (`audit`, `build`, `lint`, `max_files`,
    `smoke`, `test`, `test_map`, `timeout`)
  - `telemetry.stable` -- the 13 fields grounded above
  - `telemetry.unstable` -- `run_id`, `execution_level`, `retries`
- Create: `tools/test_contract_surface.py` -- computes the same six-category
  surface live from the current tree (a pure `current_surface()` function),
  loads the golden (SKIP with a reason, not a crash, if absent -- the golden
  deliberately does **not** ship to an installed target, see note below),
  and a pure `diff_surface(current, golden)` function reporting, per
  category: additions (fine, printed only for visibility), removals in a
  `stable` set (printed as `REMOVED (breaking)`), removals in
  `unstable` (printed as `REMOVED (warn-only)`). Exits 0 always this pass --
  report before gate, matching every other Cluster B/C/D instrument.
  **Why the golden does not join `install.py`'s `TREES`:** it is a
  self-referential fixture about *this* repository's own contract surface,
  the same category as `tools/test_*.py` itself (`SHIPPED_SUITES` already
  excludes ~40 of those from being adopted as a target's own test set for
  the identical reason -- a target's contract surface is its own, not this
  one's). `tools/test_contract_surface.py` still ships (`tools/` is in
  `TREES`), and it degrades to a named SKIP rather than a crash when the
  golden is absent, so a fresh install is never broken by this.
- Modify: `.claude/project-checks.json:test` -- add
  `"python tools/test_contract_surface.py"`
**Dependencies:** 2
**Rollback:** delete both new files; remove the `project-checks.json` line
**Preconditions:** Task 2 landed (shared file)
**Verification:**
- Run: `python tools/test_contract_surface.py`
- Expect: `0 breaking removal(s)` against the golden as committed; exits 0;
  `diff_surface()` called directly with a synthetic golden carrying one
  extra `stable` capability name and one extra `unstable` telemetry field
  not present in a synthetic current surface is shown to report exactly
  one `REMOVED (breaking)` and one `REMOVED (warn-only)` line, and a
  synthetic golden that is a strict subset of current reports zero removals
  (additions are silent-safe) -- proving the check can fail before it is
  trusted, entirely via in-memory dicts, no file mutation to revert
**Done when:** the seeded-violation proof above passes and the real diff
against the live tree is clean.

---

### Task 4: Close out -- objectives table, spec status
**Purpose:** record what changed where the layer's own knowledge docs expect
it, per this repo's own discipline.
**Files:**
- Modify: `docs/objectives.md` -- instrument table gains 3 rows (17 ->
  `test_preservation_rate.py`; 19 -> `test_idempotence.py`; 20 ->
  `test_contract_surface.py`); update the "no dedicated instrument" line.
  **Also fixes a pre-existing stale entry found while editing this exact
  line**: it still listed `22` and `24` as having no instrument despite
  both already having rows in the table above them (Cluster C's own
  closure edit added the rows but never removed the two numbers from this
  summary line) -- corrected alongside the 17/19/20 removal rather than left
  stale next to a fresh edit of the same sentence.
- Modify: `docs/specs/2026-08-21-qualitative-objective-metrics.md` -- mark
  Cluster B closed (mirroring how Cluster C and D's own closures are
  recorded).
**Dependencies:** 3
**Rollback:** revert both doc edits
**Preconditions:** Task 3 landed and its real ratios are known
**Verification:**
- Run: `python tools/test_referenced_paths.py` (docs/objectives.md path
  references stay valid) and `python tools/run_checks.py --tier all --require-test`
- Expect: `PASS` -- no broken reference, full suite still green with 3 more
  checks counted
**Done when:** `docs/objectives.md` names all three new instruments, the
stale 22/24 mention is gone, and only 13, 15, 16, 25, 27 (Cluster A) remain
in the "no dedicated instrument" line.

## Constitution gate
- [x] I Evidence -- every task names the exact command and expected output
- [x] II Test first -- each new check must be proven to flag a seeded
  violation (via pure in-memory function calls, no filesystem mutation to
  revert) before it is trusted, per the spec's own "Testing the instruments
  themselves" rule
- [x] III Smallest change -- scoped to Cluster B's 3 objectives only;
  Cluster A remains named, not built
- [x] IV Reversibility -- every task is a file create/delete or a one-line
  `project-checks.json` addition; no irreversible step
- [x] V No silent degradation -- no existing check's command or verdict
  changes; all additions
- [x] VI Mechanism -- each objective's rule is enforced by the new test file
  itself, not by this plan's prose
- [x] VII Secrets -- the one planted-secret payload in Task 1 is
  runtime-assembled exactly as `test_hooks.py` already does it, never a
  literal credential-shaped string in source

## Complexity tracking
None -- all seven articles ticked, no exception taken.

## Out of scope
- Building Cluster A (13, 15, 16, 25, 27) -- the last remaining cluster,
  named follow-on per the spec's own recommended sequence.
- Freezing agent or command names into the contract-surface golden -- not
  named by the spec's Cluster B section; separate candidate scope if wanted.
- Turning any of the three new checks into a gate (non-zero exit on a
  breaking finding) -- explicit follow-up unit per the spec's "report before
  gate" constraint, only after a baseline exists.
- Re-grading objectives 1-10 or re-running the 2026-08-20 qualitative pass
  for objectives outside Cluster B -- out of this plan's scope.

**Deviation, Task 1 (reconciled, significant):** the plan text described part (b) as firing hooks and "diffing the derived state" (files under `.claude/hooks/state/`). Grepping every `STATE = Path(...)` assignment under `.claude/hooks/{context-budget,post-tool,prompt-intake}/*.py` before writing the fixture proved that expectation wrong: **every** hook that currently writes state is one of the accumulative counters the spec's own caveat already excludes (call counts, char totals, turn timestamps) -- there is no currently-live hook that writes genuinely idempotent derived state to diff. Pivoted to the honest, safer instrument the property actually supports: **decision-hook determinism** -- firing the three confirmed-stateless decision hooks (`pre-edit`, `permission-security`, `pre-tool`) twice each with an identical payload and asserting the exit code + ALLOW/DENY verdict match. This also avoided firing `stop-finalization/06-artifact-autocommit.py` (git-mutating) and `telemetry/09-telemetry.py` (append-only) against the real repo, neither of which a repeat-fire test should touch.

**Real finding, not seeded** (found by running part (a), not by reading the spec): `.claude/layer-manifest.json` is itself NOT byte-stable across a second install. `install.py:plan()` correctly gives every already-present SEED file (`ruff.toml`, `mypy.ini`, `.github/workflows/checks.yml`, `CODEOWNERS`) a `"preserve"` action on a repeat install, but `write_manifest()`'s owned-path filter only keeps `("create", "overwrite", "unchanged", "create-stub", "create-claude-stub", "merge")` -- `"preserve"` is absent from that tuple. Confirmed directly (not just via the ratio): 4/4 SEED entries present in `_layer_owned()` after install 1, 0/4 after install 2, with zero bytes of the SEED files themselves changed. Recorded in the check's own docstring and printed as a named finding every run (installer's tree-delta ratio prints `186/187` rather than `1.0`); not fixed here -- repairing `write_manifest()` changes `install.py`'s own behavior, a different and riskier change than building a detector, mirroring Cluster D's Task 4 precedent for a found-not-fixed bug.

**Mechanical fixes from running the check, not from reading the plan:** the first draft used `test_install.py`'s own gating `check()`/`failures`/`sys.exit(1)` convention, copied by habit from the file it extends -- wrong for a Cluster B/C/D report-only instrument. Rewritten to the `main() -> int: ... return 0` / `raise SystemExit(main())` shape Cluster D's `tools/test_hook_conformance.py` actually uses. Also: `tools/test_no_slop.py --scope layer`'s `check_hook_spawn_stdin()` (a real, previously-proven-2026-08-07 trap in this exact repo) flagged the hook-firing `subprocess.run()` call for missing `stdin=subprocess.DEVNULL` -- fixed; without it the check would hang only when run through the tier, never standalone, exactly the failure mode that check exists to catch before it ships. mypy flagged `DECISION_CASES`' inferred element type as `object` rather than `dict` -- fixed with an explicit `list[tuple[str, dict]]` annotation.

---

**Deviation, Task 2:** none from the plan text. Real result: `preserved/total = 7/7 (1.0)` against the actual installer on the first run -- no bug found here, unlike Task 1. The seeded-violation self-check (a synthetic before/after pair with one byte flipped) passed on the first run.

---

**Deviation, Task 3:** none from the plan text's design. The golden's telemetry `stable`/`unstable` split was computed from `LOG.md`'s own dated entries (see "Fresh research" above) rather than guessed. Beyond the in-memory `diff_surface()` self-check the plan called for, a second, file-based proof was also run per this session's hard constraint ("proven against a REAL or deliberately seeded violation"): an extra `"FAKE_CAPABILITY_ZZZ"` and `"fake_unstable_field_zzz"` were appended directly to the committed golden file, the check correctly printed `1 breaking, 1 warn-only, 0 addition(s)` naming both, and the golden was then regenerated from the live tree (its generator script is deterministic) -- confirmed clean at `0 breaking, 0 warn-only, 0 addition(s)` before this plan's final verification pass. `git diff` on the golden path is empty relative to the intended committed content (the file was untracked/new throughout, so the revert was proven by re-running the check clean, not by `git diff --stat`).

---

**Deviation, Task 4 (reconciled):** the plan's stated Done-when said "only 13, 15, 16, 25, 27 (Cluster A) remain in the \"no dedicated instrument\" line." Writing the line correctly proved that wrong: this branch (`feat/cluster-b-rerun-safety`) was cut from main's tip `5d15067`, BEFORE Cluster D's four checks were committed on the separate, not-yet-merged `feat/cluster-d-layer-self-grading` branch -- confirmed by grepping this branch's own `tools/` for `test_hook_conformance.py` etc. (absent) before writing the doc edit. Claiming Cluster D closed here would have been false for this branch's actual tree. Corrected to name the true state: "Objectives 11, 12, 13, 15, 16, 25, 26, 27, 29 (Clusters A and D) have no dedicated instrument yet on this branch," with an explicit note that D exists independently on its own branch, not yet merged here. This is exactly the class of merge-time reconciliation `docs/objectives.md` will need regardless once both branches land -- noting it accurately now is cheaper than a silently-false claim discovered later. Also found and fixed while running Task 4's own verification command (not predicted by the plan): `README.md:174` claimed "46 suites" and `test_referenced_paths.py` counts real `tools/test_*.py` files on disk, which became 49 after this plan's 3 additions -- fixed.

**Final verification:** `python tools/run_checks.py --tier all --require-test` — `PASS: 58 check(s) green (audit, build, lint, smoke, test, typecheck)` -- up from the pre-plan baseline (55, per `LOG.md`'s 2026-08-22 entry, the same baseline Cluster D's plan cites on its own branch before Cluster D's own 4 additions) by exactly the 3 new checks this plan registered (`test_idempotence.py`, `test_preservation_rate.py`, `test_contract_surface.py`). `python tools/test_referenced_paths.py` — `All referenced-path tests passed`, live counts `suites: 49`.

## Approved
