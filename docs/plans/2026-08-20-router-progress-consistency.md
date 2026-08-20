# Close the router-disagreement and progress-checkbox gaps Implementation Plan

## Approved

**Goal:** Make the entry classifier stop calling a control/sensitive-surface
change "too small to frame," and collapse the four independently-defined
`## Progress` checkbox regexes into one, so the two duplicated-decision
mechanisms named in the 2026-08-16 audit stop disagreeing with themselves.
**Source brief:** this conversation (user asked for an implementation plan
against the 5 audit gaps in `HANDOFF.md` Pending/Next Steps and `ISSUES.md`)
**Slug:** router-progress-consistency
**Risk:** high (inferred — not yet run against the materialized file). Every
touched file matches `tools/scope.py`'s `CONTROL_PATTERNS` (`.claude/hooks/*`),
which forces `high` on its own `CLAUSE_TIER` table. Re-run
`python tools/scope.py --plan docs/plans/2026-08-20-router-progress-consistency.md`
as the first step after this plan is saved to disk and confirm before Gate 1.
**Blast radius:** two mechanisms used on every turn or every plan: the
entry-classifier (fires on `UserPromptSubmit`, silent by default today) and
the four progress-checkbox readers (plan linting in `analyze.py`, stall
detection in `chain.py`, PR-body generation in `git_ops.py`, state derivation
in `resume.py`). A regression in either reproduces this repo's own recurring
failure class: a hook or check that is silently wrong rather than loudly
broken. Mitigated by writing every new regression case before the code change
and keeping edits inside existing pure functions.
**Rollback:** every task is a self-contained diff behind an existing pure
function (`classify()`, `plan_tasks_done()`, etc.) with no migration, no
persisted state, and no schema change — `git revert` of either task's commit
cleanly restores prior behavior with no residual effect on the other task.
**Architecture:** No new router and no new shared decision-maker — both
mechanisms already exist and are documented decisions
(`decisions/2026-08-07-one-workflow-engine.md`,
`decisions/2026-08-09-one-door-into-the-chain.md`,
`decisions/2026-08-04-hooks-never-name-a-skill.md`). This plan only makes an
existing consumer import an existing source of truth instead of guessing (Task
1: entry-classifier imports `scope.py`'s own veto lists) or defining its own
copy (Task 2: four sites import one shared regex from `_hooklib.py`) — the
same "no second copy left" pattern `scope.py` itself already uses for
`_hooklib.MIGRATION_PATH_PATTERNS` and `parallel_groups.SHARED_PATTERNS`.
**Tech stack and constraints:** Python 3, stdlib only (`re`, `fnmatch`,
`importlib.util`), matching every file touched. No filesystem lookups inside
`classify()` — see Task 1's Implementation notes for why, and the Known
limitation it leaves. No behavior change for a well-formed plan's `## Progress`
block in Task 2 — only removes the theoretical divergence on a malformed one.

## Grounding (verified before planning, not assumed)

- Live-tested: `scope._match('.claude/hooks/_projectchecks.py', scope.CONTROL_PATTERNS)`
  → `True`. `scope._match('tools/run_checks.py', scope.CONTROL_PATTERNS)` →
  `False` — confirms `HANDOFF.md`'s own illustrative wording ("run_checks.py")
  was a paraphrase; the real reproduced case is `.claude/hooks/_projectchecks.py`.
- Traced `entry-classifier.classify()`'s pass order: pass 1 (`HARD_STAGE`)
  already catches any prompt containing the literal substring `.claude`
  (`r"\.claude\b"`) *before* the `TOO_SMALL` pass runs. So a fully
  directory-qualified `.claude/hooks/...` prompt is already routed correctly
  today — the real gap is a **bare filename with no `.claude` substring**, or
  a qualified path outside `.claude/` that pass 1 has no vocabulary for (e.g.
  `pyproject.toml`, `.github/workflows/*.yml` — both in `scope.py`'s
  `SENSITIVE_PATTERNS`). Confirmed: `classify("fix the version pin in
  pyproject.toml")` currently returns `"entry-small"` while
  `scope._match("pyproject.toml", SENSITIVE_PATTERNS)` is `True` — a live,
  reproducible disagreement with no directory-prefix ambiguity.
- `python tools/memory.py --paths <all 7 files below>` returned 29 entries,
  all directory-level (`.claude/`, `tools/`, `decisions/`), nothing naming
  these specific files individually. Nothing contradicts this approach; three
  decisions ground it directly (cited above).
- `tools/analyze.py` and `tools/chain.py`/`tools/git_ops.py` already carry a
  private `_load(rel, name)` importlib helper (one copy per file, an accepted
  existing pattern — not something this plan centralizes, that would be scope
  creep). `tools/resume.py` has none yet; Task 2 adds one, mirroring the
  other three verbatim.

## File map

- Modify: `.claude/hooks/user-prompt/01-entry-classifier.py` — TOO_SMALL pass
  defers to `scope.py`'s veto lists before returning `entry-small`.
- Modify: `tools/test_entry_classifier.py` — regression cases for the fix and
  its documented limitation.
- Modify: `.claude/hooks/_hooklib.py` — add `PROGRESS_BOX_PATTERN` /
  `PROGRESS_TASK_BOX`, the one shared definition of a Progress checkbox.
- Modify: `tools/analyze.py` — `PROGRESS_RE` becomes an import of
  `_hooklib.PROGRESS_TASK_BOX` via the existing `_load()`.
- Modify: `tools/chain.py` — `PROGRESS_TICK` becomes an import of the same,
  with ticked-only filtering moved into the counting call site.
- Modify: `tools/git_ops.py` — `_PROGRESS_RE` becomes the shared prefix
  pattern text plus its own title-capture suffix (unchanged behavior).
- Modify: `tools/resume.py` — `_CHECKBOX` becomes the shared pattern (adds
  the `Task \d+` requirement `plan_tasks_done()` was missing); adds a private
  `_load()` mirroring the other three files.
- Modify: `tools/test_analyze.py`, `tools/test_chain.py`,
  `tools/test_git_ops.py`, `tools/test_resume.py` — one new case per file
  proving the shared pattern is used and behavior is unchanged for a
  well-formed plan.

## Progress
- [x] Task 1 — entry-classifier defers to scope.py's control/sensitive veto
- [x] Task 2 — one shared Progress-checkbox regex, four sites import it

## Tasks

### Task 1: entry-classifier defers to `scope.py`'s control/sensitive veto
**Purpose:** a prompt naming a path `scope.py` would call `control-surface` or
`sensitive-surface` (high risk) never gets waved through as "too small to
frame" — closing the reproduced HANDOFF disagreement without building a
second router.
**Files:**
- Modify: `.claude/hooks/user-prompt/01-entry-classifier.py:classify` — add
  `import fnmatch`, `import importlib.util`; add a private `_load(rel, name)`
  helper (verbatim copy of the one in `tools/chain.py`); add
  `_control_or_sensitive_patterns()` (lazy-loads `tools/scope.py` once,
  returns `CONTROL_PATTERNS + SENSITIVE_PATTERNS`); add
  `_names_control_or_sensitive_path(text)` (iterates `re.finditer(_PATH,
  text)`, returns `True` if any matched token `fnmatch.fnmatch`es any pattern
  from `_control_or_sensitive_patterns()`); change the `TOO_SMALL` branch in
  `classify()` from `if _hit(TOO_SMALL, text): return "entry-small"` to
  `if _hit(TOO_SMALL, text) and not _names_control_or_sensitive_path(text):
  return "entry-small"` (falls through to the next pass otherwise, exactly
  like today's non-match case).
- Modify: `.claude/hooks/user-prompt/01-entry-classifier.py` docstring on
  `classify()` — the line "Pure and dependency-free on purpose" is no longer
  true; narrow it to "pure over its own reasoning; reads `tools/scope.py`'s
  fixed pattern lists once as an input, the same tradeoff `scope.py` itself
  makes importing `_hooklib`" — leaving a false purity claim in place is
  exactly the prose-outran-wiring class this repo's `ISSUES.md` keeps finding
  in itself.
- Test: `tools/test_entry_classifier.py` — see Verification.
**Dependencies:** none
**Implementation notes:** `_PATH` already exists
(`r"\b[\w./-]+\.(py|js|jsx|ts|tsx|md|json|ya?ml|toml|css|html|rs|go|java|rb)\b"`)
and runs against `text`, which `classify()` has already lowercased — compare
against `CONTROL_PATTERNS`/`SENSITIVE_PATTERNS` as-is, both already lowercase,
so no extra normalization is needed (unlike `scope._norm`, which only handles
`\`-vs-`/` and a leading `./`, neither of which a prompt string carries).
**Known, deliberate limitation** (name it in the docstring, do not silently
drop it): a bare filename with no directory component that lives under a
wildcard directory pattern (`.claude/hooks/*`, `.claude/agents/**`) is NOT
resolved — e.g. "fix a typo in _hooklib.py" still returns `entry-small`,
because catching it would require checking the token against the real
filesystem tree, which would make `classify()` depend on repo state beyond
its two fixed inputs (the prompt string, `scope.py`'s pattern lists) and break
the determinism `test_entry_classifier.py` relies on. Only literal-filename
patterns (`pyproject.toml`, `.claude/workflow.md`, …) and directory-qualified
paths already in the prompt are caught.
**Rollback:** revert the one commit; `classify()` returns to its prior
behavior with no other file affected.
**Preconditions:** none — `tools/scope.py`'s `CONTROL_PATTERNS`/
`SENSITIVE_PATTERNS` already exist and are stable public module attributes.
**Verification:**
- Run: `python tools/test_entry_classifier.py`
- Expect: exit 0, including new cases —
  `classify("fix the version pin in pyproject.toml") != "entry-small"`;
  `classify("fix the version check in capability_layer/cli.py") != "entry-small"`;
  a cross-check that `scope._match("pyproject.toml", scope.CONTROL_PATTERNS +
  scope.SENSITIVE_PATTERNS)` is `True`, proving the two now agree on the same
  fact; and the documented limitation pinned as still-true:
  `classify("fix a typo in _hooklib.py") == "entry-small"` (a regression here
  means the limitation note has gone stale, not that something broke).
  **Deviation, reconciled:** the plan originally named
  `.github/workflows/checks.yml` as the second case. Live-testing before
  writing it found that phrasing never reaches `TOO_SMALL` at all — the
  `[^.]{0,60}` gap in `SMALL_LOCATED` can never cross the leading dot in
  `.github/`, a separate, pre-existing quirk unrelated to this fix. Swapped
  to `capability_layer/cli.py` (in `SENSITIVE_PATTERNS`, no leading dot),
  confirmed red before the fix and green after.
- Executed: `PYTHONIOENCODING=utf-8 python tools/test_entry_classifier.py`
  → `OK: the entry predicate matches the labelled corpus`, all cases green.
  Hook fired directly via `HOOK_PAYLOAD` for three real prompts: a known-good
  case still renders its `entry-unframed` block unchanged; both new
  sensitive-surface prompts now print nothing (fall through to silence
  rather than `entry-small`) — the intended effect.
- Run: `python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 54 check(s) green` (no suite count regression — the two new
  tests live inside `test_entry_classifier.py`, an existing suite).
**Done when:** the reproduced HANDOFF case
(`.claude/hooks/_projectchecks.py`-shaped prompts) and the two new
sensitive-surface cases all classify as *not* `entry-small`, the full existing
labelled corpus in `docs/evals/trigger-queries.json` still passes unchanged,
and the docstring's purity claim matches what the code actually does.

### Task 2: one shared Progress-checkbox regex, four sites import it
**Purpose:** `analyze.py`, `chain.py`, `git_ops.py` and `resume.py` read a
plan's `## Progress` checkboxes with one definition instead of four
independently-typed ones that had already begun to disagree.
**Files:**
- Modify: `.claude/hooks/_hooklib.py` — add, near `DECLARE_LINE`:
  `PROGRESS_BOX_PATTERN = r"^- \[( |x|X)\]\s+Task\s+(\d+)\b"` and
  `PROGRESS_TASK_BOX = re.compile(PROGRESS_BOX_PATTERN, re.M)`, with a
  docstring naming all four current call sites so a fifth site knows to reuse
  it rather than retype it.
- Modify: `tools/analyze.py:58-61` — replace the local `PROGRESS_RE`
  definition with `PROGRESS_RE = _load(".claude/hooks/_hooklib.py",
  "hooklib_for_analyze").PROGRESS_TASK_BOX` (identical pattern text today, so
  this is a no-op for every existing `test_analyze.py` case).
- Modify: `tools/chain.py:79-83` — replace `PROGRESS_TICK`'s local definition
  with a use of `_hooklib.PROGRESS_TASK_BOX` (already loaded via the file's
  existing `_load(".claude/hooks/_hooklib.py", "hooklib_for_chain")` call);
  update `plan_progress()`'s counting line (`ticked +=
  len(re.findall(PROGRESS_TICK, text))`) to `ticked += sum(1 for m in
  hooklib.PROGRESS_TASK_BOX.finditer(text) if m.group(1).lower() == "x")`,
  since the shared pattern has capture groups and matches both ticked and
  unticked boxes, unlike the old ticked-only local regex.
- Modify: `tools/git_ops.py:74-79` — replace `_PROGRESS_RE`'s local pattern
  string with `hooklib.PROGRESS_BOX_PATTERN + r"\s*[—\-:]*\s*(.*)$"`, compiled
  with `re.M` — keeps the title-capture group git_ops needs while sharing the
  box/task-number prefix text verbatim.
- Modify: `tools/resume.py` — add a private `_load(rel, name)` helper
  (verbatim copy of `tools/chain.py`'s); replace `_CHECKBOX = re.compile(r"^-
  \[([ xX])\]", re.M)` with `_CHECKBOX =
  _load(".claude/hooks/_hooklib.py", "hooklib_for_resume").PROGRESS_TASK_BOX`
  — `plan_tasks_done()` is already scoped to the `## Progress` section via
  `_PROGRESS_SECTION` first, so this only changes behavior for a malformed
  section (a checkbox line not shaped `Task N`), never for a well-formed plan.
- Test: `tools/test_analyze.py`, `tools/test_chain.py`,
  `tools/test_git_ops.py`, `tools/test_resume.py` — see Verification.
**Dependencies:** none (independent of Task 1; touches an entirely disjoint
file set)
**Implementation notes:** `_hooklib.PROGRESS_TASK_BOX`'s two capture groups
are `(mark, task_number)` — `analyze.py` and `chain.py` only ever read
`m.group(1)` (the mark) or use `findall`/`finditer` counts, so the group
shape is compatible with existing call sites without further changes beyond
what's listed above. `git_ops.py`'s existing three-group tuple unpacking
(`mark, num, title in _PROGRESS_RE.findall(...)`) is preserved exactly since
the shared prefix keeps groups 1-2 and the appended suffix adds group 3.
**Rollback:** revert the one commit; each of the four files returns to its
own private regex with no cross-file effect, since none of them import
anything from `_hooklib.PROGRESS_TASK_BOX` elsewhere.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_analyze.py && python tools/test_chain.py && python tools/test_git_ops.py && python tools/test_resume.py`
- Expect: all four exit 0, each including a new case: a plan fixture whose
  `## Progress` section contains a malformed line (`- [x] done` — no `Task
  N`) proves NOT counted by `resume.plan_tasks_done()` where before the fix it
  would have been (the closed drift); and a well-formed fixture (`- [x] Task
  1 — title`) proves unchanged behavior across all four modules.
- Run: `python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 54 check(s) green`.
**Done when:** all four sites read `_hooklib.PROGRESS_TASK_BOX` (or its raw
pattern text) instead of their own copy, a malformed checkbox is treated
identically by all four, and no existing suite's assertions changed meaning.

**Executed:** `analyze.py`/`chain.py`/`git_ops.py`/`resume.py` all now source
the box pattern from `_hooklib.py` (three via `_load()`, `resume.py` gained
the helper). `resume.plan_tasks_done()` and `chain.plan_progress()` both had
to change their consuming logic, since the shared pattern carries two capture
groups where each site's private one carried fewer — reconciled inline, not a
plan deviation (the plan's own Implementation notes anticipated exactly this
for both). Ran `python tools/test_analyze.py`, `test_chain.py`,
`test_git_ops.py`, `test_resume.py` individually — all four green, including
the new malformed-checkbox case (red before the fix, green after) and the
mixed ticked/unticked case. `python -m mypy` on all nine touched files: clean.
Fired `_hooklib.PROGRESS_TASK_BOX` directly against realistic mixed content
(ticked, unticked, and a constitution-gate box) — correctly distinguishes all
three. `python tools/run_checks.py --tier all --require-test`:
`PASS: 54 check(s) green`.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — every new case is written and run red before the code
  change (see each task's Verification; `executing-plans` ticks a task only
  once its own check passes, which enforces this at execution time)
- [x] III Smallest change — no refactor beyond what each task requires; the
  wildcard-directory filesystem-lookup case and the four files' `_load()`
  duplication are both named and deliberately left alone (see Out of Scope)
- [x] IV Reversibility — both tasks are plain regex/logic edits behind
  existing pure functions; no migration, no persisted state
- [x] V No silent degradation — the one known limitation (Task 1) is named in
  the docstring and pinned by a test, not silently dropped
- [x] VI Mechanism — every rule this plan adds is enforced by a new test
  assertion, never by prose alone
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why (the other 3 of the 5 audit gaps)

- **Objective 2 — per-turn description cost (17,900 ch/turn).** Not an
  implementation task. The one lever (trimming skill descriptions) has
  measured evidence pointing the wrong way — `code-review` scored
  `trigger_rate 0.0` and the docs say the fix for under-triggering is a
  *more* specific description, not a shorter one. `HANDOFF.md` names the next
  step as a live ~$81 `tools/eval_triggers.py` run, which spends real money
  and needs the user's explicit go-ahead before it runs — that approval is a
  separate decision, not a code change, and does not belong in this plan.
- **Gate 2 has never fired end-to-end.** Not separately buildable. It is an
  emergent property of a real unit of work actually reaching delivery through
  the chain, not something a task can construct. This plan reaching Gate 2 is
  itself a data point toward closing it, but engineering a fake trigger for it
  would prove nothing and was rejected on that basis.
- **`secret-in-branch` / `dependency-risk` firing organically.** Not fixable
  by writing code — these are observational facts about what has actually
  happened on a real branch, and forcing one artificially (as already tried
  once for `secret-in-branch`, per `HANDOFF.md`) proves the mechanism works in
  a fixture, which is already known; it does not make either fact true.
- **The rest of the router-disagreement space.** This plan closes the
  specific, reproduced control/sensitive-surface veto gap. Widening the
  entry-classifier to also weigh `scope.py`'s `volume`/`spread`/`shared-surface`
  clauses (which need a real diff, not just prompt text, and so cannot be
  computed at `UserPromptSubmit` time at all) is a larger, separate design
  question this plan does not decide.
