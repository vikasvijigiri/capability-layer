# Instruments for the 15 uninstrumented objectives — Design

**Date:** 2026-08-21
**Owner skill:** `brainstormer` (spec only — no code, no plan)
**Scope:** Notion objectives **11, 12, 13, 15, 16, 17, 18, 19, 20, 22, 24, 25,
26, 27, 29** — the fifteen with no dedicated instrument in
`docs/objectives.md`'s "Where each one is measured" table.

## Problem

Twenty-three of the thirty objectives that grade this layer now name a command
that produces their number. Fifteen do not. They are graded by a one-time human
read — `docs/research/2026-08-20-notion-objectives-audit.md`, a real evidence-
backed pass, but one that cannot be re-run and therefore cannot detect
regression. An objective nothing can re-measure is an objective that silently
decays between audits.

The failure mode to avoid is louder than the gap. Three gates were deleted from
this repository for asserting a judgement they could not make
(`03-review-gate`, `05-docs-gate`, `05-docs-required` — see
`tools/test_no_slop.py`'s own docstring), and the review gate went further: it
self-invalidated its receipts and the model then forged one. So the bar here is
not "produce a number for each of the fifteen." It is: **every number traces to
something already computed, to a real external project's own conformance
vocabulary, or to a structural fact about a file** — and where neither exists,
the honest answer is a named qualitative cadence, not a fabricated ratio.

This is the same discipline the three instrumented units this session followed
(`duplicate_rate` is arithmetic over counters that already existed; `retries`
surfaces `resume.py`'s and `loop.py`'s own outputs rather than recomputing
them). Nothing below invents a proxy.

## Constraints

- **Additive only.** No existing gate, hook, check, or shipped telemetry field
  changes behaviour. No existing objective's grade may regress.
- **Off the hot path.** Objectives 2, 3, and 6 (tokens, context, latency) are
  themselves graded per-turn. Every instrument here lands in the `test` or
  `audit` tier, or in `--tier all`. Nothing new fires on `PostToolUse`,
  `UserPromptSubmit`, or `Stop`. An instrument that taxes every turn would
  damage three already-green objectives to measure a fourth.
- **Report before gate.** Each new check ships printing a ratio and exiting 0.
  It becomes gating only in a follow-up unit, once a baseline exists. This
  mirrors `tools/bench.py --save`, which "baselines *comparisons*, never
  *judges*" — the mechanism objective 30 is already graded on.
- Python 3, stdlib only (`ast`, `json`, `pathlib`), matching every existing
  tool. No new dependency.

---

## Approaches considered

### Approach 1 — Rubric scorecard on a cadence

Write a rubric per objective; a human or a dispatched agent grades all fifteen
into a dated scorecard each release. No code at all.

Cheap, immediately available, and honest about which objectives are judgements.
**Rejected as the primary answer:** it is the deleted-gate shape. A scorecard is
a receipt, and this repository has already learned twice that a receipt asserting
a review happened is worse than no gate — it reads as coverage while proving
nothing, and nothing stops it being written without the work behind it. It also
does not regress-detect: two scorecards a month apart tell you a grade changed,
not which commit changed it. Kept as a *component* for the residue (see
objective 11 below), never as the mechanism.

### Approach 2 — One composite "objective score"

Compute a single 0-100 per objective from weighted sub-signals, emitted into
telemetry alongside the shipped fields. One dashboard, trivially trended.

**Rejected:** the weights are invented. There is no source — not the Notion
spec, not a comparable project — that says observability is 40% schema coverage
and 60% audit-trail completeness. A composite is exactly the "invented proxy
that merely looks quantitative" the user's constraint names, and it is *worse*
than no number because it launders three honest signals into one unfalsifiable
one. It also destroys the property that makes the shipped metrics useful: you
can point at `duplicate_rate` and say which counter produced it.

### Approach 3 — Instrument typed to the objective, clustered by mechanism ★

Give each objective the instrument its *kind* admits: a counter where something
already counts, a structural boolean where the objective is about whether a file
or field exists, a fixture-corpus run where the objective is about behaviour in
a repository that is not this one, and an explicit qualitative cadence where
none of those honestly apply. Then group the fifteen by the machinery they
share, so each group is one buildable deliverable.

**Chosen.** It is the only approach that satisfies both hard constraints at
once. Each instrument is defensible individually — every one below cites either
an already-computed local value, a named real project's own conformance
criterion, or a structural fact — and none of them needs a weight, a receipt, or
a judgement encoded as arithmetic. It costs more than Approach 1 and yields no
single headline number like Approach 2; both are prices worth paying.

**What would change my mind:** if the fixture-corpus machinery (Cluster A) turns
out to cost more than the objectives it grades are worth, Cluster A alone drops
back to Approach 1's cadence while B, C and D proceed. That is a per-cluster
decision, not a reason to abandon the shape.

---

## The four clusters

| Cluster | Objectives | Count | Coherent because |
|---|---|---|---|
| **A — Target-matrix conformance** | 13, 15, 16, 25, 27 | 5 | All five ask "does this work in a repository or host that is not this one"; all five are answered by one fixture corpus of synthetic target repos plus the adapter conformance fields. |
| **B — Re-run safety** | 17, 19, 20 | 3 | All three are "run it twice, or run it over something that already exists, and nothing is lost"; all three are diffs against a prior state. |
| **C — Telemetry completeness and adaptivity** | 18, 22, 24 | 3 | All three are pure reads over data `09-telemetry.py` and `docs/evals/trigger-queries.json` already produce; no new hook, no new corpus. |
| **D — Layer self-grading** | 11, 12, 26, 29 | 4 | All four statically grade this layer's *own source* — hooks and tools — and all four land as `tools/test_*.py` entries in `project-checks.json`. |

---

## Cluster C — Telemetry completeness and adaptivity (18, 22, 24)

Shared mechanism: `tools/bench.py` gains a read over `.claude/hooks/state/telemetry.jsonl`;
one new `tools/test_router_dispersion.py`. Zero new hooks.

### Objective 22 — Observable and auditable

*"every meaningful decision, change, verification result and failure traceable,
without excessive logging."*

**Instrument, two parts.**

1. **Schema coverage** = populated fields ÷ (populated + `unavailable`) in the
   latest `telemetry.jsonl` row. Pure arithmetic over `09-telemetry.py`'s
   `build_snapshot()` and its existing `UNAVAILABLE_FIELDS` dict — both already
   written every turn. Additionally, a **required subset must be 100%**: every
   field this harness *can* observe is populated, and anything absent appears in
   `unavailable` with a stated reason rather than silently missing.
2. **Trace completeness** (boolean): every telemetry row carries the chain
   `slug` and `fingerprint` that ties it to a unit of work. Already present in
   the `chain` field; nothing asserts it.

**Grounding — OpenTelemetry attribute requirement levels.** OTel defines
Required ("All instrumentations MUST populate the attribute"), Conditionally
Required, Recommended, and Opt-In, and states that "Consumers of telemetry can
detect if a telemetry item follows a specific semantic convention by checking
for the presence of a `Required` attribute." That is precisely the shape here:
classify the Notion §21 field list into Required (observable in this harness)
and Opt-In (in `UNAVAILABLE_FIELDS`), then count presence. The `unavailable`
map is already this repo's independent reinvention of the same idea — this
names it and makes it countable.
Source: https://opentelemetry.io/docs/specs/semconv/general/attribute-requirement-level/

**Why this is not a proxy:** the denominator is the spec's own field list and
the numerator is a file the layer already writes. Nothing is estimated.

### Objective 24 — Self-adapting and self-healing

*"detect, diagnose locally, repair when safe, re-verify, escalate only when
current capability is insufficient."*

**Instrument.** **Local-repair ratio** = ladder outcomes at `repair`/`restore` ÷
all outcomes that entered the ladder, with the `block`/`retreat` count reported
alongside. Computed as an aggregate over the `retries.rung` field already
written into every telemetry row by the `four-more-spec-metrics` unit
(2026-08-21). No new hook; `tools/bench.py` gains one line.

**Grounding — the objective's own vocabulary maps one-to-one onto a shipped
mechanism.** "Repair when safe … escalate only when current capability is
insufficient" is `tools/loop.py:rung()`'s existing
repair/restore/rebase/retreat/block ladder, verbatim in concept. The metric
surfaces a verdict the CLI already prints rather than deriving a new one — the
same move as `duplicate_rate` and `retries` themselves. Externally this is the
standard SRE auto-remediation-rate framing, but the local mechanism is the
stronger citation: the spec's words and the code's rung names already agree.

**Caveat to record in the plan:** a low ratio is not automatically a failure.
Objective 1 (minimal human interference) and objective 24 pull against each
other at the margin, and the audit already flagged that `chain.py`'s escalate-
rather-than-auto-repair posture is "likely correct per objective 1." The metric
reports the ratio; it must not gate on a target value without a decision record
naming the intended balance.

### Objective 18 — Adaptive, not prescriptive

*"detect maturity, risk and state, then choose the workflow rather than forcing
every project through one process."*

**Instrument.** **Route dispersion over the labelled corpus.** Replay
`docs/evals/trigger-queries.json` through `.claude/hooks/user-prompt/01-entry-classifier.py`
and `tools/scope.py`, and assert: (a) **non-degeneracy** — more than one
distinct route/verdict is produced across the corpus, reported as the
distribution over shapes; (b) **agreement** — where both classifiers fire on the
same input, their verdicts are consistent.

**Grounding.** The corpus exists and objective 8 already replays it, so this is
a second read of a shipped instrument, not new machinery. Its own `_method`
field cites `anthropics/skills` skill-creator's description-optimization method
(~20 queries per skill, half should-trigger, half genuine near-misses), which is
standard labelled-corpus classifier evaluation. Clause (b) is grounded in real
local counter-evidence: the audit records that "the two mechanisms disagreed
until this session's `fix/router-progress-consistency` unit closed the *specific
reproduced case*, not the whole class." This metric is the regression test for
the rest of that class.

**Why dispersion and not accuracy:** a prescriptive system is one that returns
the same answer regardless of input. Dispersion measures exactly that failure.
Accuracy against labels is objective 8's instrument and is not duplicated here.

---

## Cluster D — Layer self-grading (11, 12, 26, 29) — Closed 2026-08-22

Built in `docs/plans/2026-08-22-cluster-d-layer-self-grading.md`:
`tools/test_hook_conformance.py` (12), `tools/test_import_independence.py`
(26), `tools/test_no_slop.py --scope portability` extended to `.py` logic
files (29), `tools/test_instrumented_surface.py` (11) — plus
`tools/test_context_cost.py` (already existed, added the same day this
spec's own #11 finding named it, but was unwired until this unit) wired into
`.claude/project-checks.json`'s gating `test` array. See that plan's
Progress block for the concrete, real (not synthetic) findings each
instrument produced when actually run, including a second unwired-coverage
gap (`tools/test_smoke.py`) the corrected objective-11 instrument surfaced
beyond the one this section already named.

Shared mechanism: static parse of this layer's own Python and JSON; each lands
as a `tools/test_*.py` in `project-checks.json`'s `test` list.

### Objective 11 — World-class engineering

*"practices, architecture, validation, observability and operational discipline
consistent with high-performing production engineering organizations."*

**Instrument — a floor, explicitly not the objective.** **Instrumented-surface
coverage** = live-wired hooks and `tools/*.py` with a resolving entry in
`project-checks.json`'s `test_map` ÷ all of them. Both inputs are already parsed
(`test_hook_registration.py` reads `settings.json`; `test_project_checks.py`
reads the map).

**Grounding.** The repo's own `_why_test_map` note already concedes `test_map`
"is a coverage CLAIM and nothing proves its judgement." This makes the claim
countable without pretending it proves quality. The audit's one concrete #11
finding — `01-context-cost.py`, live-wired since before that session with zero
tests anywhere in the repo — is exactly one miss this ratio would have printed.
Externally, `anthropics/skills`'s `quick_validate.py` is the precedent for a
structural validator run over every artifact of a kind (it hard-fails on
frontmatter shape, kebab-case names, a 64-char name limit and a 1024-char
description limit — structure only, never quality).

**Honest residue.** "World-class" is irreducibly a judgement and no ratio closes
it. The coverage number is a *floor*: it can prove the objective is being
missed, never that it is met. The qualitative half stays qualitative, with a
named cadence: `python tools/test_no_slop.py --scope repo` plus a dated re-read
of the audit document at each release, recorded in `LOG.md`. Saying so is the
deliverable; a rubric pretending otherwise is Approach 1's rejected shape.

### Objective 12 — Production-grade by default

*"robust, testable, observable, maintainable, secure, deployable, unless the
task explicitly calls for a prototype."*

**Instrument.** **Hook-contract conformance rate** — per live-wired hook, a
boolean vector, reported as n/N conforming with the failing clause named:

- one responsibility (one state file / one concern),
- payload read through `_hooklib.load_payload()`,
- explicit exit-code semantics (a reporting hook cannot fail its event),
- a declared bounded timeout,
- a representative-payload case in `tools/test_hooks.py`.

`test_hook_standards.py` and `test_hook_policy.py` already enforce a subset;
this counts and reports across the whole set rather than only failing on one.

**Grounding — `github/awesome-copilot`'s `hooks.instructions.md`, verbatim:**
"One hook, one responsibility"; "Keep hooks synchronous, bounded, and
non-interactive"; "Test scripts by piping representative JSON payloads into them
manually"; `timeoutSec` optional, default 30 seconds, host kills the process
past it. This is a real, published hook contract from a comparable project, and
this layer can be scored against it clause by clause.
Source: https://github.com/github/awesome-copilot/blob/main/instructions/hooks.instructions.md

### Objective 26 — Low-coupling / composable

*"each capability independently usable, replaceable and reusable; no unnecessary
dependency on one path."*

**Instrument.** An **import-independence contract**: declare which units of the
layer must not depend on each other — hook families ↔ each other, `tools/*` ↔
`.claude/hooks/*` except through `_hooklib` — and fail on a violating edge,
direct or indirect. Implemented as a static import-graph walk with stdlib `ast`;
reports declared-contract count and violation count.

**Grounding — `import-linter`.** It defines exactly these contract types:
*independence* ("check that a set of modules do not depend on each other by
checking that there are no imports in any direction between the modules, even
indirectly"), *forbidden modules*, and *layers*. The concept is adopted; the
dependency is not, since a stdlib `ast` walk over ~40 files is smaller than
adding a package to a zero-dependency tool set.
Source: https://import-linter.readthedocs.io/en/latest/contract_types.html

**Required allowlist.** The duplicated `_load()` helper across four tool files
is an *accepted, recorded* exception (`docs/plans/2026-08-20-router-progress-consistency.md`,
Grounding). It must be an explicit allowlist entry with that citation, never a
silent pass — an exception nothing names is indistinguishable from a violation
nobody noticed.

### Objective 29 — No hardcoded project truth

*"project-specific facts discovered, configured or learned, never embedded into
universal workflow logic."*

**Instrument.** **Extend `tools/test_no_slop.py --scope portability` to logic
files.** Today its `check_portability()` reads only `.md` under
`.claude/skills/`, `.claude/agents/` and `.claude/commands/` (confirmed at
`tools/test_no_slop.py:170`). Objective 29's own words are "never embedded into
universal *workflow logic*" — and the `.py` under `.claude/hooks/` and `tools/`
*is* that logic, currently unread by this check. Metric: count of repo-specific
literals in universal logic — this repo's name, sibling repo names, hardcoded
branch prefixes, absolute paths, dated claims — with an allowlist for genuinely
configured defaults.

**Grounding — local, and already load-bearing.** `check_portability()` is this
repo's own on-point implementation of objective 29; it found seven real false-
anywhere-else claims the first time it was run, and its comment block already
articulates the exact principle ("the lesson is generic and worth keeping;
'deleted on 2026-08-02' is provenance, and provenance does not travel"). This
extends a proven check to the surface it was always about. Externally this is
the 12-factor "config in the environment" principle.

**A known instance it would catch immediately:** `tools/resume.py`'s
`BRANCH_PREFIX` is hardcoded to `"feat/"`, which the `four-more-spec-metrics`
unit recorded as a live bug (it makes `derive_state` unreachable on a `docs/`
branch). That is project truth embedded in universal logic, already logged,
currently uncounted by anything.

---

## Cluster B — Re-run safety (17, 19, 20)

Shared mechanism: fixture install targets (extending `test_install.py`'s
existing harness) plus one checked-in golden contract file.

### Objective 19 — Idempotent and repeatable

*"repeated execution converges without duplicating work, corrupting artifacts or
introducing inconsistency."*

**Instrument.** **Second-run delta = 0.** Install into a fixture target twice
and diff the tree; fire the full hook set twice against the same payload and
diff the *derived* state.

**Grounding — Ansible Molecule's `idempotence` step**, the canonical form of
this check: the converge playbook runs a second time and the step fails if any
task reports changed — "The second run should normally end with `changed=0`."
Molecule adds no logic of its own; it runs the action twice and diffs. Same
shape here. Reinforced by `awesome-copilot`'s hook rule, verbatim: "Make hooks
deterministic and idempotent — Re-runs should not create drift."
Sources: https://docs.ansible.com/projects/molecule/workflow/ ·
https://github.com/github/awesome-copilot/blob/main/instructions/hooks.instructions.md

**Load-bearing caveat.** Counter hooks (`tool-cost.json`, `read-cost.json`,
`human-cost.json`, …) are *intentionally* accumulative — a second fire
*must* change them. The assertion is scoped to installed artefacts and derived
state, never to monotonic counters, or the check is wrong by construction and
gets switched off within a day. `test_install.py` already proves the
`--dry-run` half ("writes nothing at all. Not 'writes less' — nothing").

### Objective 17 — Non-destructive integration

*"coexist with existing workflows; preserve working behavior; avoid unnecessary
restructuring."*

**Instrument.** **Preservation rate** = files present in a fixture target before
install that are byte-identical after ÷ all of them, expected 100% outside the
declared additive set; plus zero bytes written under `--dry-run` (already
proven). Extends `test_install.py`'s existing fixture machinery rather than
adding new machinery.

**Grounding.** `install.py`'s own `PRESERVE` list is the local contract, and
`test_install.py`'s docstring already names the properties ("`CLAUDE.md` and
`.claude/project-checks.json` are never overwritten … `settings.json` is merged,
never replaced"). What is missing is the *ratio over the whole tree* — today
only the named files are asserted, so a file nobody thought to name is
unprotected. Externally this is the `terraform plan` / `helm --dry-run` check-
mode family, the same lineage as Molecule above.

### Objective 20 — Backward-compatible where practical

*"preserve contracts, interfaces and behavior unless a deliberate, justified
breaking change is required."*

**Instrument.** **Contract-surface diff against a frozen golden.** Freeze the
layer's public contract surface into a checked-in golden file; a check diffs
current against golden and **fails on a removal or a rename, while allowing
additions**. A deliberate break is landed by updating the golden in the same
commit, which makes the break visible in review instead of invisible in a diff.

**Grounding — `cargo-semver-checks`.** It "detects the kind of version bump
you're making (major, minor, or patch), then scans for API changes that might be
inappropriate for that bump," runs in CI as `cargo semver-checks && cargo
publish`, and is used by Amazon and Google to prevent breaking published crates.
Same mechanism, no Rust: a machine-readable public surface, a frozen baseline,
and a CI check that distinguishes additive from breaking.
Source: https://github.com/obi1kenobi/cargo-semver-checks

**Highest-value single item in the fifteen** — objective 20 is the only one the
audit graded **Unmeasured** (not even Amber): "No versioning or
compatibility-testing convention observed for the layer's own contract surface."

**Resolved 2026-08-22** (`docs/research/2026-08-22-cluster-d-b-grounding-refresh.md`):
include telemetry fields in the frozen golden, in an explicit two-tier
split — `stable` (removal or rename fails the check) and `unstable` (free
addition; removal or rename only warns, never fails). This is the direct
transplant of a verified mechanism, not an invented tier: `cargo-semver-checks`
excludes features literally named `unstable`/`nightly`/etc. from
breaking-change detection by default, and separately supports downgrading
individual lints to `warn` via `[package.metadata.cargo-semver-checks.lints]`
— tracked and visible, never silently unguarded. A field promotes
`unstable` → `stable` only by a deliberate, reviewed edit to the golden
file, never automatically, preserving the "additive change is visible in
review" property the whole golden-diff mechanism exists for. Cluster B
itself (17, 19, 20) is not built by this resolution — only the design
question is answered, ahead of that cluster's own implementation unit.

---

## Cluster A — Target-matrix conformance (13, 15, 16, 25, 27) — CLOSED 2026-08-22

Shared mechanism: **one fixture corpus of synthetic target repositories**, plus
the adapter conformance fields. Five objectives, one piece of machinery — which
is the whole reason they cluster.

**Resolved:** the fixture corpus is generated at test time by a fixture
builder inline in `tools/test_target_matrix.py`, never checked into the
repo. `test_install.py`'s own `fresh_repo()` is the precedent, and this
repo fought hard to shrink its installable payload (1,586,874 →
1,172,851 bytes, `TASK.md`'s "Make the layer portable" entry) — checking in
a five-stage corpus would partially undo that objective-14 win. The corpus
stayed small in practice: five stages plus one non-Python stack, a handful
of files each, built and torn down in one run
(`docs/plans/2026-08-22-cluster-a-target-matrix.md`).

**Delivered:** `tools/test_target_matrix.py`, one file covering all four
objectives against the shared corpus — stage-fixture pass rate (15),
real-structure detection plus zero check-leakage from this repo's own
gating list (16), non-Python stack coverage via a bare Go layout (25), and
a zero-migration boolean (27). Objective 13 needed no new instrument
(already Green via `.claude/adapters/*.json` +
`test_portability_contract.py`). Measured cost: +~4.7s on the fast tier
(39.6s → 44.3s, one clean before/after run with the file moved aside and
restored) — reported honestly per the spec's own "say so rather than hide
it" instruction, not hidden.

### Objective 13 — Universal / generic

**Instrument.** **Adapter conformance completeness** = adapters whose every
`capabilities` entry is either `host-managed` or backed by a non-null
`conformance` receipt ÷ all declared adapters. Reported with the blocking
capabilities named.

**Grounding — `obra/superpowers`, `porting-to-a-new-harness.md`.** Its
Definition of Done is six criteria, all required, including "Acceptance test
passes with exact transcript" — support is never claimed from metadata, only
from a named receipt. This repo's `test_portability_contract.py` docstring
already states the same rule locally ("A JSON manifest cannot prove that another
host executed a bridge; it can only stop this repository from advertising one
before a host-specific conformance command exists"). The metric counts what that
rule already forbids advertising. Today `codex.json` carries `"conformance":
null` with four `bridge-required` capabilities — a real, currently-uncounted
number.
Source: https://github.com/obra/superpowers/blob/main/docs/porting-to-a-new-harness.md

**Structural, boolean-per-adapter — no number is invented.** This objective is
already Green; the instrument exists to detect regression, not to re-litigate.

### Objective 15 — Stage-agnostic

**Instrument.** **Stage-fixture pass rate** — install, then `tools/recon.py`,
then `run_checks.py --tier fast`, against one synthetic target per stage the
objective itself names: greenfield (empty), partial, legacy (no tests), broken
(failing build), undocumented (no README). Pass = no crash, and recon returns a
non-empty map. Directly closes the audit's Amber note: "no evidence of testing
against a genuinely broken or undocumented target repo specifically."

**Grounding.** `test_install.py` already runs a fresh install into a Python and
a Node target and requires that target's own tier green — this extends a proven
harness along a second axis (stage rather than language). Superpowers'
acceptance-transcript requirement is the external precedent for "support is a
run that happened, not a claim."

### Objective 16 — Repository-agnostic

**Instrument.** Over the *same* corpus: `tools/recon.py` must report the
target's real structure (detected language, test command, entry points), and
`_projectchecks.py` must **detect** rather than assume — asserted as **zero
checks resolved from this repo's own `project-checks.json`** when running inside
a fixture. That single assertion is the difference between discovering a
repository and assuming one, and it is why 15 and 16 share a cluster.

### Objective 25 — Technology-agnostic

**Instrument.** **Stack coverage** — the corpus includes at least one
non-Python, non-Node target, and install seeds no Python-specific config there.
Closes the audit's exact Amber wording: "`install.py` seeds Python lint config
only into hosts that have Python … not verified against a non-Python, non-Node
stack." A Go *layout* (a `go.mod` and a package directory) suffices — nothing
here compiles the fixture, so no toolchain need be installed on the machine
running the check, which keeps the corpus cheap and CI-portable.

### Objective 27 — Progressively adoptable

**Instrument.** **Zero-migration boolean** — after install into each fixture,
the target's own pre-existing build/test command still runs unchanged, and the
count of files the target had to move or rename is 0. Structural; no external
precedent needed beyond superpowers' "Real users can install through native
mechanisms" DoD item and `install.py`'s own additive-by-design posture.

---

## Recommended path forward

**Build Cluster C first**, then D, then B, then A.

**C first**, for three reasons that compound:

1. **It is the same shape as the two units already shipped this session** —
   pure reads over data `09-telemetry.py` already writes, plus one replay of a
   corpus objective 8 already replays. Lowest blast radius of the four, and the
   pattern is proven twice over on this exact tree.
2. **Objective 22's instrument is the meta-instrument.** Schema coverage is the
   number every later cluster reports into; building it first means B and D land
   with somewhere to report rather than each inventing a surface.
3. **Two of its three metrics need no new machinery at all** — 22 is arithmetic
   over `UNAVAILABLE_FIELDS`, 24 is an aggregate over the `retries.rung` field
   that shipped hours ago. Only 18 needs a new file.

**D second**, because it contains the only *concrete defect* the audit found
(`01-context-cost.py` live-wired with zero tests) and the only *already-logged*
bug an instrument here would catch (`resume.py`'s hardcoded `BRANCH_PREFIX`).
Measuring something that is currently broken pays back immediately.

**B third**: highest single-item value (objective 20 is the only Unmeasured of
the fifteen) but it needs the golden-surface question answered first.

**A last**: five objectives for one mechanism is the best ratio of the four, but
it is also the largest build (a five-target corpus) and the cluster whose
objectives are already graded best — four Green or Green-Amber out of five. It
buys regression detection on things that currently work, which is real but
strictly less urgent than measuring what is currently broken.

---

## Two loose threads from the same audit — neither is a blocker

Both re-verified on this tree, 2026-08-21.

**E0-E5 execution-level router (audit Gap A).** Still absent — grepping
`E0`/`execution_level`/`execution level` repo-wide returns only
`09-telemetry.py`'s `UNAVAILABLE_FIELDS` entry, two self-aware comments in
`01-entry-classifier.py` (lines 224 and 421), and prose in `docs/`. **Not a
prerequisite for any of the fifteen.** The plausible dependency is objective 18,
and it does not hold: 18 is measured against the *shipped* five-shape classifier
and `scope.py`, both of which exist and both of which the corpus already
exercises. It would *enrich* objectives 18 and 22 — `execution_level` is one of
the fields keeping 22's schema-coverage ratio below 1.0 — but an honestly-named
gap is exactly what that ratio is designed to report. **Separate candidate unit.**

**Agent-catalogue decision record.** Still absent — `decisions/` holds twelve
records, none about the agent catalogue; `.claude/agents/` holds 11 custom
files against the spec's stated ~6-8. **Not a blocker, and the dependency runs
the opposite way to the intuitive one.** Objective 26's low-coupling instrument
does not need the decision to exist; rather, Cluster D's import-independence
contract produces the evidence the decision should rest on — whether those 11
agents are genuinely independent single-lens reviewers or a coupled set that
wants consolidating. Writing the record first would be deciding before
measuring, which is the failure the whole spec is arranged against. **Separate
candidate unit, sequenced after Cluster D.**

---

## How this preserves every other objective

The user's constraint was explicit: no other objective may be affected. The
mechanisms above satisfy it structurally, not by promise.

- **Nothing runs per turn.** Every instrument is a `test`- or `audit`-tier
  entry, or a `bench.py` read invoked on demand. Objectives 2, 3, 6 and 7 are
  graded on per-turn cost and see no new work at all.
- **Nothing modifies an existing gate's verdict.** Cluster C adds read paths and
  a new file. Cluster D adds new `tools/test_*.py` files. Cluster B extends
  `test_install.py`'s fixtures additively and adds one golden. Cluster A adds
  fixtures. The one *modification* proposed anywhere is widening
  `check_portability()`'s file set (objective 29) — an opt-in scope that no
  per-turn gate runs, whose own docstring records that this is deliberate.
- **Report before gate**, per Constraints. A new check that exits 0 while
  printing a ratio cannot regress any objective's grade on the day it lands.
- **Objective 30 is protected by the same rule that grades it.** No threshold
  here is refit from a single measurement; each ships as a reported number with
  a baseline recorded, mirroring `bench.py --save`.

## Testing the instruments themselves

Each new check gets its own regression cases in the suite it joins, and each
must be proven to **fail** on a seeded violation before it is trusted — the
repository's Article II discipline, and the specific defence against a fourth
false-confidence gate. Concretely: objective 29's widened check must flag
`resume.py`'s `BRANCH_PREFIX` before it is considered working; objective 11's
coverage ratio must print a miss for a deliberately unmapped file; objective
20's golden diff must fail on a deleted capability name; objective 19's
double-run must fail against a deliberately non-idempotent fixture.

## Out of scope

- **Objective 2 (tokens).** Needs the ~$81 paid `eval_triggers.py` run; `TASK.md`
  records it as its own unit, explicitly not to be bundled.
- **Re-grading objectives 1-10.** The 2026-08-16 pass stays the last full one
  until re-run with its own named instruments.
- **Building the E0-E5 router or the agent-catalogue record.** Both are separate
  candidate units, per the section above.
- **Turning any new check into a gate.** Follow-up unit, after a baseline.
