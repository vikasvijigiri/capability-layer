# Cut this layer's own token overhead: skill-metadata duplication, skill-cost telemetry honesty, and doc-cap enforcement Implementation Plan

## Approved

Gate 1 approved via `ExitPlanMode` after one revision round (first draft
of Task 1 rejected for pruning `when_to_use` rather than merging it, and
for not checking body content against a real benchmark before excluding
it — both resolved with primary-source evidence from `anthropics/skills`,
see Architecture below).

**Deviation from `implementation`'s default concurrent-dispatch
behavior, recorded per that skill's own rule ("either amend the plan
file with the reason or revert to the plan"):** `parallel_groups.py`
reports round 1 (tasks 1+2) at concurrency 2, which would normally mean
two worktrees and two `implementer` dispatches. Not done here — both
tasks are small, fully disjoint text edits (frontmatter fields and one
test assertion; two telemetry files) with no coordination risk, so
worktree/subagent overhead does not pay for itself at this size. Branch
`trim-skill-metadata-duplication`, base commit `5041301f5fc6e14
31df6359475ff996a5a207651` (on `chore/dedupe-layer-post-merge`), created
before Task 1; all three tasks executed directly and sequentially in
that branch.

**Goal:** Three independent, low-risk fixes to this layer's own overhead,
approved together as one unit: (1) consolidate `when_to_use` into
`description` and tighten every skill's `description` toward the
canonical ~100-word target, backed by a new mechanical check so it can't
silently drift back up, (2) correct `02-skill-cost.py`/`bench.py` so the
reported skill-load figure states its own dedup-blindness instead of
implying a verified 1:1 real-cost reading, (3) make `documentation/
SKILL.md` actually invoke the doc-length cap check that already exists
and is already wired into `test_map`, but that its own procedure never
tells the model to run. Skill body content is explicitly out of scope —
see Architecture.

**Source brief:** `TASK.md` ("Implement world-class SessionStart bootstrap
scaffolding" unit, plus this session's follow-on scoping); grounding
evidence in `docs/research/2026-08-22-dynamic-routing-vs-fixed-policy.md`.

**Slug:** trim-skill-metadata-duplication

**Risk:** high — forced by `control-surface` (every touched path is under
`.claude/`, this layer's own control surface) and `spread` (18 declared
paths). Per `tools/scope.py --plan docs/plans/2026-08-22-trim-skill-metadata-duplication.md`:
`risk: high -- high forced by: control-surface` / `scope: major -- vetoed
by: control-surface, spread`. Not a judgment call — a control-surface
change is high regardless of how mechanical the edit is. This does not
change Gate 2's requirement (still owed regardless of tier).

**Blast radius:** All 14 `.claude/skills/*/SKILL.md` frontmatter blocks
(the per-turn skill listing every session pays for); `.claude/hooks/
context-budget/02-skill-cost.py`'s state schema; `tools/bench.py`'s
report output; `.claude/skills/documentation/SKILL.md`'s body procedure
and Routing section. No skill body content besides `documentation`'s own
procedure text, no routing logic, no new hook — frontmatter text, one
telemetry report line, and one skill's own written procedure.

**Rollback:** `git revert` the commit. All three changed areas are pure
text (frontmatter fields, a docstring, a print statement, a skill's own
procedure prose) with no schema migration or persisted state shape
change — a revert restores prior behavior exactly.

**Architecture:** First draft of Task 1 proposed only pruning
`when_to_use`'s overlap with `description`. Rejected at Gate 1 review:
the user asked to research the actual canonical format rather than
guess. Fetched `anthropics/skills`' `skill-creator/SKILL.md` directly
(not a search summary) and it settles this decisively — **the canonical
Agent Skills format has no `when_to_use` field.** Only `name` and
`description` exist; Claude reads only those two to decide triggering,
and the spec's own guidance is *"all 'when to use' information in the
description rather than in the body [or a separate field]."*
`when_to_use` is this repo's own invention (`guide/
how_to_create_skills.md:132-134`'s stated purpose — "if a skill fires
too rarely, add `when_to_use`" — describes a corrective lever, not a
permanent second field every skill should carry). So Task 1 now merges
`when_to_use` into `description` and deletes the field, then tightens
`description` toward the same source's stated target: *"~100 words
ideal."* Current range is 139-188 words per skill — over budget even
before merging `when_to_use` in.

The same primary source also settles the body-content question: *"Keep
SKILL.md under 500 lines."* Checked all 14 — largest is `task-analysis`
at 372 (74% of the ceiling); none breach it. No evidence-backed case to
trim body content exists, and the user confirmed this scope explicitly:
bodies are untouched by this plan.

**Revised again during implementation (Task 1, before any file was
edited):** the plan initially called for a new hard `<= 130`-word test
assertion here, reasoned by analogy to `test_doc_entries.py`'s
headroom convention. Reading `tools/test_process_router.py` itself
before writing that assertion surfaced a direct, on-point,
already-reasoned decision against it: lines 66-70 already carry a
`SOFT_DESC = 500`-char soft check (a NOTE, not a failure) for exactly
this field, with its own stated reason — *"a hard ceiling turns each
new skill into a hunt for words to cut from unrelated ones, and the
trigger phrases are the part that would go first — which is the part
that makes a skill fire at all."* 500 chars already approximates the
same ~100-word canonical target this plan is aiming for. Adding a new
hard cap would directly override that reasoning without engaging it.
Confirmed with the user: **no new test assertion.** Task 1 relies on
the existing `SOFT_DESC` NOTE as its only mechanical signal, and
tightening `description` is done in service of that existing soft
target, not a new hard one — the same shrinkage, without reintroducing
the risk that reasoning was written to avoid.

Confirmed pre-existing hard constraint that stays true either way:
`tools/test_process_router.py:141-144` caps `description`+`when_to_use`
combined at 1,536 chars per skill and must stay green — trivially true
once `when_to_use` is deleted. Task 3 adds no new mechanism
either: `documentation/SKILL.md:15-18` already states plainly that
hooks watching these files were tried and deleted twice (once blocking
and deadlocking, once warn-only and superseded by a pull-style slash
command) — this repo's own direction for this file family is pull, not
push. `tools/test_doc_entries.py` is already registered against `LOG.md`
and `ISSUES.md` in `.claude/project-checks.json`'s `test_map`; Task 3
only makes `documentation`'s own procedure pull it at the right moment,
matching the "Mandatory validator" convention every other skill in this
repo already uses in its Routing section.

**Tech stack and constraints:** Plain Markdown/YAML frontmatter edits and
two Python files already following this repo's existing hook-docstring
conventions (see Task 2's grounding). No new test assertion (dropped
during implementation — see the revision note above), no new
dependency, no new test framework, no new test file. Constraint: merging
must not drop a trigger phrase that
`docs/evals/trigger-queries.json` labels `should_trigger` for that skill,
and must keep each skill's "Do NOT use..." disambiguation clause —
verified for free via `new_skill_check.py`'s reachability check and
`eval_triggers.py --all --dry-run`, never the paid `--all` (no `--dry-run`)
run.

## Grounding — existing patterns this plan follows

| Category | Pattern | Citation |
|---|---|---|
| Canonical Agent Skills frontmatter has exactly two fields | `name`, `description` — no `when_to_use`; "all 'when to use' information in the description" | `anthropics/skills`' `skill-creator/SKILL.md` (fetched directly this session) |
| Canonical `description` target | "~100 words ideal" | same source |
| Canonical body ceiling | "Keep SKILL.md under 500 lines" | same source |
| `when_to_use`'s original, narrower intended scope in this repo | a corrective lever for an under-triggering skill, not a default second field | `guide/how_to_create_skills.md:132-134` |
| The hard combined-length gate (stays true, now trivially) | `description`+`when_to_use` <= 1536 chars | `tools/test_process_router.py:141-144` |
| This repo's own convention for a target-vs-enforced-cap gap | `test_doc_entries.py`'s hard 20/16-line checks against `formats.md`'s ~15/~12-line stated targets, with explicit stated headroom | `tools/test_doc_entries.py:38-44` |
| Hook docstrings stating their own measurement limits | `02-skill-cost.py`'s own docstring already models this for a different limitation ("the field name carrying the skill's identifier... is not documented") | `.claude/hooks/context-budget/02-skill-cost.py:12-19` |
| Free, deterministic reachability check per skill | `new_skill_check.py --all` fires the router at each skill's own keywords, no spend | `tools/new_skill_check.py:1-25` |
| The paid, must-not-run-casually trigger eval | `eval_triggers.py` spends one `claude -p` call per query; `--dry-run` is free | `tools/eval_triggers.py:14-20` |
| Doc-length enforcement mechanism (Task 3) already exists, and hooks that watched these files were tried and deleted twice | `05-docs-gate.py` (blocking, deadlocked, deleted 2026-08-02), `05-docs-required.py` (blocking, deleted same day), `04-docs-staleness.py` (warn-only, deleted anyway — superseded by the pull-not-push `/wip` command). This repo's own direction is pull over push for this file family. | `decisions/2026-08-07-derived-state-over-stored-state.md:57-60`; `LOG.md` 2026-08-02 entries; `.claude/skills/documentation/SKILL.md:15-18,149-153` |
| The check Task 3 wires in is not new — it is already registered and already scoped correctly | `.claude/project-checks.json`'s `test_map` already maps `LOG.md` and `ISSUES.md` to `python tools/test_doc_entries.py`, so `tools/run_checks.py --scoped` already runs it when either file is in the changed-file scope. Nothing needed building; `documentation/SKILL.md`'s own procedure just never told the model to run it before finishing. | `.claude/project-checks.json:94-96` |
| Every other skill in this repo names its own required check in its Routing section | e.g. `task-analysis`: "Mandatory validator: `python tools/analyze.py --slug`" | `.claude/skills/task-analysis/SKILL.md` Routing section |

`python tools/memory.py --paths` over the touched files returned only
directory-level `.claude`/`decisions` hits (nothing specific to
`when_to_use` trimming or this telemetry line) — no prior attempt or
caution recorded to reconcile with.

## File map

- Modify: `.claude/skills/architecture/SKILL.md` — merge `when_to_use` into `description`, tighten toward ~100 words
- Modify: `.claude/skills/capability-layer-maintenance/SKILL.md` — same
- Modify: `.claude/skills/code-review/SKILL.md` — same
- Modify: `.claude/skills/data-analysis/SKILL.md` — same
- Modify: `.claude/skills/debugging/SKILL.md` — same
- Modify: `.claude/skills/documentation/SKILL.md` — same (frontmatter only, in Task 1; its body is separately touched by Task 3)
- Modify: `.claude/skills/implementation/SKILL.md` — same
- Modify: `.claude/skills/refactoring/SKILL.md` — same
- Modify: `.claude/skills/release-git/SKILL.md` — same
- Modify: `.claude/skills/repository-navigation/SKILL.md` — same
- Modify: `.claude/skills/research/SKILL.md` — same
- Modify: `.claude/skills/security/SKILL.md` — same
- Modify: `.claude/skills/task-analysis/SKILL.md` — same
- Modify: `.claude/skills/testing/SKILL.md` — same
- Modify: `.claude/hooks/context-budget/02-skill-cost.py` — add dedup-limitation note to the counter's own docstring and state
- Modify: `tools/bench.py` — append the caveat to the skill-body-loads report line
- Modify: `.claude/skills/documentation/SKILL.md` — add the doc-length
  validator step to "The order" and name it in the Routing section

## Progress

- [x] Task 1 — Merge `when_to_use` into `description` across all 14 skills
- [x] Task 2 — State the dedup limitation in skill-cost telemetry
- [x] Task 3 — Wire the existing doc-length check into `documentation`'s own procedure

## Tasks

### Task 1: Merge `when_to_use` into `description`, tighten toward ~100 words, across all 14 skills
**Purpose:** conform to the canonical Agent Skills format (no
`when_to_use` field exists in it) and cut the oversized per-turn listing
cost at its actual source (`description` itself, not just the duplicate
field). No new enforcement mechanism (see the plan's revision note) —
`tools/test_process_router.py`'s existing `SOFT_DESC = 500`-char NOTE
already signals this target; a new hard cap was considered and dropped
as contradicting that file's own on-record reasoning.
**Files:**
- Modify: `.claude/skills/architecture/SKILL.md` (frontmatter)
- Modify: `.claude/skills/capability-layer-maintenance/SKILL.md` (frontmatter)
- Modify: `.claude/skills/code-review/SKILL.md` (frontmatter)
- Modify: `.claude/skills/data-analysis/SKILL.md` (frontmatter)
- Modify: `.claude/skills/debugging/SKILL.md` (frontmatter)
- Modify: `.claude/skills/documentation/SKILL.md` (frontmatter only — its body is Task 3's, not this task's)
- Modify: `.claude/skills/implementation/SKILL.md` (frontmatter)
- Modify: `.claude/skills/refactoring/SKILL.md` (frontmatter)
- Modify: `.claude/skills/release-git/SKILL.md` (frontmatter)
- Modify: `.claude/skills/repository-navigation/SKILL.md` (frontmatter)
- Modify: `.claude/skills/research/SKILL.md` (frontmatter)
- Modify: `.claude/skills/security/SKILL.md` (frontmatter)
- Modify: `.claude/skills/task-analysis/SKILL.md` (frontmatter)
- Modify: `.claude/skills/testing/SKILL.md` (frontmatter)
**Dependencies:** none
**Implementation notes:** For each of the 14 skills: (1) read
`description` and `when_to_use`; fold any phrase from `when_to_use` that
is not already covered by `description` into `description`. (2) Delete
the `when_to_use` field entirely. (3) Tighten `description` toward the
existing `SOFT_DESC = 500`-char soft target where doing so does not
drop a phrase `docs/evals/trigger-queries.json` labels `should_trigger`
for that skill, and does not drop the skill's own "Do NOT use..."
disambiguation clause (these exist specifically to prevent misrouting
between skills sharing vocabulary — task-analysis's "Do NOT use to
implement it (implementation), to diagnose a failure (debugging), to
choose between approaches (architecture), or for a direct question" is
the sharpest example and must survive). A skill landing over 500 chars
after a good-faith tightening pass is not a task failure — it prints a
NOTE, by this file's own design, not a FAIL. Do not touch any `SKILL.md`
body content below the frontmatter (Task 3 is the one exception, in its
own task, on `documentation` only).
**Rollback:** `git checkout -- <file>` per file, or revert the commit.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exits 0, including the existing combined-cap check (now
  trivially satisfied with `when_to_use` absent); any `NOTE:` lines for
  a skill still over the 500-char soft target are expected output, not
  a failure.
- Run: `python tools/new_skill_check.py --all`
- Expect: exits 0 — every skill still reachable by the router at its own
  keywords after the rewrite.
- Run: `python tools/eval_triggers.py --all --dry-run`
- Expect: lists the same query set per skill as before the edit (no
  `should_trigger` query silently dropped); this is the free path — do
  not run without `--dry-run`.
**Done when:** all three verification commands pass, `when_to_use` no
longer appears in any of the 14 frontmatter blocks, and the combined
`description budget` total `test_process_router.py` reports at the end
of its run is lower than the pre-edit baseline (8,923 chars / 14
skills, mean 637 — captured before this task started).

**Result:** all three verification commands passed clean (0 FAIL across
`test_process_router.py`'s full suite, `new_skill_check.py --all`'s 14
skills, and `eval_triggers.py --all --dry-run`'s 14-skill corpus
listing). `description budget: 8264 chars across 14 skills (~2066
tokens injected every turn, mean 590)` — down from the 8,923/637-char
baseline in description text alone, with the entire separate
`when_to_use` field eliminated on top (roughly 150-250 more chars per
skill that no longer exists anywhere).

**One extra, in-scope fix found while editing `documentation`'s
frontmatter:** a stray `  - formats.md` line sat directly under
`when_to_use:`, which YAML was silently folding into that field's
scalar value as literal trailing text ("... or catch me up. -
formats.md"). Confirmed via a direct `yaml.safe_load` check before
touching it. Not a new field — `formats.md` is already correctly
referenced in the skill's own body prose — so this was pre-existing
rot in the exact block this task already modifies, not scope creep;
removed rather than left to attach itself to the merged `description`
instead.

**Two rounds of self-caused verification failures, both fixed in place
before moving on** (recorded per this skill's own HARD-GATE — a
verification is not "done" until read back): the first full rewrite of
all 14 descriptions dropped quote marks around trigger phrases and
shortened "Use this whenever"/"Use this proactively" to "Use
whenever"/"Use proactively", which silently broke three existing
mechanical checks in `test_process_router.py` this task never set out
to touch (`lists at least 6 trigger phrases` — a regex over `"quoted"`
substrings, failed on all 14; `says to fire without being asked` — an
exact-phrase check, failed on 10; `leads with its capability, not a
condition` — a 12-word first-sentence cap, failed on 2 where a
semicolon merged two sentences into one long first clause). All three
were re-fixed by restoring quoted phrases, the exact fire-clause
wording, and a period after the first sentence, then re-verified green.

**Full-tier check before delivery:** `python tools/run_checks.py
--scoped` refused (scope computed `major`, vetoed by `spread`/
`unmapped` — by design, an over-broad change escalates rather than
under-checking). `python tools/run_checks.py --tier all --require-test`
found one real issue outside this plan's anticipated scope:
`test_no_slop.py --scope portability` flagged Task 3's own new Routing
prose ("...and this repo's own history on that file family is pull, not
push") for naming a specific repository in portable layer prose — this
layer is meant to install into any repository, so provenance like "this
repo's history" is false everywhere else it ships. Reworded to keep the
lesson (hooks were tried and deleted; direction is pull not push)
without the provenance clause. Re-ran clean: `PASS: 55 check(s) green
(audit, build, lint, smoke, test, typecheck)`.

**Commit approach** (implementation's "say which, before Task 1" —
stated here retrospectively since all three tasks were small,
independent, and executed as one continuous unit): execute the run,
commit once, covering all three tasks together.

### Task 2: State the dedup limitation in skill-cost telemetry
**Purpose:** `02-skill-cost.py` sums on-disk `SKILL.md` size × invocation
count with no way to know whether Claude Code's own native dedup (repeat
invocation with identical rendered content emits a short "already loaded"
note instead of the full body) applied — so `bench.py`'s "skill-body
loads" line currently reads as a precise real-cost figure it cannot
back. State the limitation where both the counter and its report live.
**Files:**
- Modify: `.claude/hooks/context-budget/02-skill-cost.py:1-30` (module docstring)
- Modify: `tools/bench.py:367-375` (the skill-body-loads report block)
**Dependencies:** none (independent of Task 1 — different files, no
ordering constraint; both may run in the same or separate rounds)
**Implementation notes:** In `02-skill-cost.py`'s docstring, add a
paragraph next to the existing "field name... not documented" caveat
(lines 12-19) stating: this counter increments on every `Skill`-tool
invocation observed and adds that skill's on-disk file size, regardless
of whether Claude Code's own content-addressed dedup (identical rendered
content across invocations emits a short marker instead of the full body
again) applied to that particular call — so `calls`/`chars` is an upper
bound on real per-session cost, not a measured one. In `tools/bench.py`,
after the `f"\nthis session's skill-body loads: {skill_calls:,}  "`
line (367-371), append one short caveat clause to the printed string,
e.g. `"  (upper bound -- does not know which calls Claude Code's own "
"dedup already served for free)"`, matching the existing terse
parenthetical style used two lines below for `unattributed`.
**Rollback:** revert the docstring/print-string edit; no state-file
schema change, so no migration to undo.
**Preconditions:** none.
**Verification:**
- Run: `python tools/bench.py`
- Expect: the "this session's skill-body loads" line prints the new
  caveat clause, and the numeric fields are unchanged in shape (still
  parses as `calls`, `chars`, `~tok`, `unattributed`).
- Run: `python -c "import ast; ast.parse(open('.claude/hooks/context-budget/02-skill-cost.py', encoding='utf-8').read())"`
- Expect: no `SyntaxError` (docstring edit did not break the module).
**Done when:** both commands succeed and the printed report and hook
docstring each name the dedup limitation in one sentence.

### Task 3: Wire the existing doc-length check into `documentation`'s own procedure
**Purpose:** `tools/test_doc_entries.py` already caps `LOG.md`/`ISSUES.md`
entries and is already registered in `.claude/project-checks.json`'s
`test_map`, so `tools/run_checks.py --scoped` already runs it whenever
either file changes — but `documentation/SKILL.md`'s own procedure never
tells the model to run it before finishing, and its Routing section says
"Mandatory validator: none." No new hook (two blocking predecessors for
this exact file family were tried and deleted; a third, warn-only one was
also deleted as redundant with a pull-style command — see Grounding
above) — this task only makes the skill pull the check that already
exists, at the moment it matters.
**Files:**
- Modify: `.claude/skills/documentation/SKILL.md:37-40` ("The order", step 4)
- Modify: `.claude/skills/documentation/SKILL.md:149-153` (Routing section)
**Dependencies:** none (independent of Tasks 1-2; touches a different
skill's body content, not its frontmatter)
**Implementation notes:** In "The order" (currently: 1. gather evidence,
2. decide which docs, 3. read formats.md, 4. request write permission
then write, 5. state what was written), insert a new step between 4 and
5: after writing any entry to `LOG.md` or `ISSUES.md`, run `python
tools/test_doc_entries.py` and fix the entry (cut it to size or split it)
before moving to step 5 if it reports a failure for that file. Renumber
the existing step 5 to step 6. In the Routing section, replace "Mandatory
validator: none, and nothing warns either... Recording is entirely on
you now" with a line naming `python tools/test_doc_entries.py` as the
mandatory validator when `LOG.md` or `ISSUES.md` was written this turn —
matching the exact phrasing convention `task-analysis`'s own Routing
section already uses for `tools/analyze.py`. Do not touch
`formats.md`, the seven-file ownership list, or any other section of
`documentation/SKILL.md`.
**Rollback:** `git checkout -- .claude/skills/documentation/SKILL.md`, or
revert the commit.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: exits 0 — the edited skill still only references paths that exist.
- Run: `python tools/test_process_router.py`
- Expect: exits 0 — `documentation`'s frontmatter is untouched by this
  task, so routing stays unaffected.
- Manual: re-read the edited "The order" and Routing sections and confirm
  the new step names the exact command and the exact two files it
  applies to (no vague "verify the entry" wording).
**Done when:** both commands pass and `documentation/SKILL.md` no longer
states "Mandatory validator: none" while a mechanism it names
(`test_doc_entries.py`) already exists and already runs on these two
files via `run_checks.py --scoped`.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — n/a: no new behavior or test assertion is added
  (see the revision note); existing `test_process_router.py` is the
  regression guard and is run, not newly written
- [x] III Smallest change — frontmatter across 14 files, one report
  line, and one skill's own procedure text; no new hook, no new test
  assertion (dropped during implementation as contradicting an
  existing, on-record decision — see the revision note), no new file
- [x] IV Reversibility — plain `git revert`, no schema/state migration
- [x] V No silent degradation — no check is skipped; the paid
  `eval_triggers.py --all` run (no `--dry-run`) is explicitly named as
  not run, by design, and is not required for this plan's own verification
- [ ] VI Mechanism — **exception, recorded in Complexity tracking below.**
  The ~100-word target is enforced only by the pre-existing `SOFT_DESC`
  NOTE, which does not fail the build. A new hard test was considered
  and deliberately not added.
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
- **VI Mechanism** — not ticked. `tools/test_process_router.py:66-70`
  already reasoned, on record, against a hard description-length cap:
  *"a hard ceiling turns each new skill into a hunt for words to cut
  from unrelated ones, and the trigger phrases are the part that would
  go first."* This plan's own first draft of Task 1 proposed exactly
  such a cap before that reasoning was found; re-reading the file it
  would have modified, before writing the assertion, surfaced the
  conflict. Confirmed with the user: keep the existing soft NOTE only.
  The risk this leaves: `description` length can drift back up over
  time with nothing failing the build — accepted, on the same grounds
  the original decision accepted it, not because it was skipped here.
