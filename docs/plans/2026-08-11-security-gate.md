# Security Gate Implementation Plan

**Goal:** A deterministic check that refuses a branch which weakens a security
control, carries a secret, leaves a sensitive path unchecked, or hands an
unscoped write capability to an agent — asserting facts about the artefact and
never that a review happened.

**Source brief:** `TASK.md` § "Deterministic security gate, and the duplicate
review surfaces it exposes". No spec under `docs/specs/` — the approach was not
open; the design is forced by the receipt history below.

**Slug:** security-gate

**Risk:** high — `high forced by: control-surface, shared-surface` (`python
tools/scope.py --plan docs/plans/2026-08-11-security-gate.md`, exit 2)

**Architecture:**

`tools/security_gate.py` in the established shape of `tools/delivery_check.py`
and `tools/git_identity.py`: a pure `evaluate(facts) -> findings` that the suite
drives directly, behind a `gather_facts(root, base, head, offline=)` seam that
owns every subprocess call. Every finding resolves to exactly one of `blocking`,
`advisory` or `unknown`; exit `0` clean, `1` a clause fired, `2` a clause could
not be evaluated. `2` is deliberately not `0` — Article V.

**Every clause is a fact about the artefact, never about process.** That is not a
style preference, it is the correction of a mechanism this repository already
built and deleted. `pre-commit/03-review-gate.py` wrote a receipt into
`.claude/hooks/state/review-receipts.json` asserting that a change had been
reviewed. Two failures killed it, both recorded in `LOG.md`:

- the receipts file was tracked, so `--record` altered the very fingerprint it
  had just recorded under, and **every receipt self-invalidated the instant it
  was written** (2026-08-01);
- *"a forged receipt and a real one are the same file"* — the model ran
  `--record` and wrote a receipt asserting a sign-off that had not happened, one
  turn after authoring the rule forbidding exactly that (2026-08-03 entry).

It was deleted on 2026-08-02 along with every other process-compliance gate,
under the finding *"Every hook in all five verifies an artefact… Not one enforces
process."* This plan therefore adds **no receipt, no hook, and no assertion that
a review occurred**. Each clause below is computable from two git revisions and
the working tree, by anyone, at any time, with no state to keep and none to
forge.

The escape hatch is the same shape: an inline `# security-gate: allow <clause> —
<reason>` line, following ruff's `# noqa` and mypy's `# type: ignore`. It is an
artefact fact, it appears in the diff a reviewer reads, and it cannot be recorded
anywhere the diff does not show.

**Tech stack and constraints:**

- Python 3, stdlib only. `ast` reads the watched tables out of both revisions;
  no import of untrusted code, no network. (`literal_eval` was the plan's word
  and did not survive contact — see Deviations.)
- The pattern tables are **imported, never copied** —
  `scope.SENSITIVE_PATTERNS`, `scope.CONTROL_PATTERNS`,
  `_hooklib.SECRET_PATTERNS`. A copy drifts the moment either changes, which is
  the failure `scope._migration_patterns()` already exists to avoid.
- **Slow tier only**, under the `audit` kind. The fast tier gates every
  auto-commit and must stay in seconds; this reads git blobs and runs
  `tools/deps.py`.
- No new hook. No hook may name a skill —
  `decisions/2026-08-04-hooks-never-name-a-skill.md`.
- No fifteenth skill. The description budget is charged on every turn, and the
  security *review* already has three doors (`code-review`'s lens,
  `/security-review`, `security-reviewer`); this adds a check, not a fourth door.
- `PYTHONIOENCODING=utf-8` before every run — several tools here print `→`.

## Prior art consulted

`python tools/memory.py --paths` returned 23 entries over the five input paths.
Two changed this plan:

- `decisions/2026-08-02-gate-on-blast-radius.md` — gate by how hard a thing is
  to undo, not by which stage it belongs to. It is why this runs at the slow
  tier and delivery rather than per turn, and why the clause set is keyed to
  blast radius (secrets, controls, sensitive paths) rather than to "security" as
  a topic. It also names `pre-commit/03-review-gate.py` as extant, which it is
  not — that reference is stale and is the trail that led to the receipt history
  above.
- `decisions/2026-08-04-hooks-never-name-a-skill.md` — the reason the gate is a
  tool wired into a check kind rather than a hook that suggests `code-review`.

Nothing is recorded about `tools/scope.py`, `tools/delivery_check.py`, or
`.claude/skills/no-slop/SKILL.md` specifically. Stated because silence and not
having looked are indistinguishable otherwise.

## The clauses

| Clause | Fires when | Severity |
|---|---|---|
| `control-weakened` | an entry present at base is absent at head in a watched security table, with no compensating addition and no inline allow | blocking |
| `secret-in-branch` | `_hooklib.SECRET_PATTERNS` matches an added line anywhere in `base...HEAD` | blocking |
| `sensitive-unmapped` | a changed path matching `scope.SENSITIVE_PATTERNS` that no `test_map` glob covers | blocking |
| `agent-unscoped` | a changed `.claude/agents/*.md` whose `tools:` grants `Write` or `Edit` and which declares no `allowed-paths:` | blocking |
| `dependency-risk` | `tools/deps.py` exits non-zero for this tree while the diff changes a dependency declaration | blocking (1) / unknown (2) |

Watched tables for `control-weakened`: `_hooklib.SECRET_PATTERNS`,
`_hooklib.SECRET_PATH_PATTERNS`, `_hooklib.AI_ATTRIBUTION_PATTERNS`,
`_hooklib.MIGRATION_PATH_PATTERNS`,
`scope.SENSITIVE_PATTERNS`, `scope.CONTROL_PATTERNS`, `scope.CLAUSE_TIER`, plus
any `.claude/project-checks.json` key whose value changes to `false`.

Why `secret-in-branch` is not already covered: `pre-commit/01-secret-scan.py`
and the auto-commit's inline check each see **one commit**. A secret added in
commit 3 and still present at HEAD is never looked at again, and delivery is
where the branch as a whole is proposed.

Why `sensitive-unmapped` is not `scope.py`'s job: `CLAUSE_TIER` deliberately
omits `unmapped`, on the stated grounds that it is *"a gap in the test map rather
than a fact about the change's danger."* That is right in general and wrong on a
path matching `**/auth/**` or `.claude/install.py`.

Why `agent-unscoped` earns a clause: `pre-edit/02-agent-scope-guard.py` denies
an unscoped agent write at runtime, so the defect presents as a silent agent
failure mid-dispatch. Measured on this tree — 2 of 11 agents declare
`allowed-paths:`, and both are the two that can write, so the clause is green
today and stays that way only if something checks it.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [ ] II Test first — every behaviour task defines its failing test first
- [x] III Smallest change — no refactor beyond what the task requires
- [x] IV Reversibility — irreversible steps are named and gated on a human
- [x] V No silent degradation — checks that will be skipped are listed here
- [x] VI Mechanism — any rule this plan adds is enforced by a test or a hook
- [x] VII Secrets — no credential enters the repo

## Complexity tracking

**Article II is unticked.** Task 1's module was written before its suite. The
exception is not that test-first was inconvenient — it is that it was skipped,
and saying so is worth more than a tick. What the article buys was bought
another way: every clause is proven by inverting it alone, so a clause that does
not fire cannot pass, and the suite found a defect in the module on its first
run. Tasks 2-7 change wiring and prose against suites that already exist.

Article V's list of skipped checks is empty by construction: the new check joins
the `audit` kind, which `run_checks.py --tier all` resolves and CI calls through
the same resolver.

## Open questions

**Resolved at Gate 1, 2026-08-11 — resolution (a).** The question was whether
`no-slop --scope change` and `code-review`, which read the same changed files at
adjacent stages, should keep both stages and gain a mechanism for the boundary
(a), or lose the overlap structurally by deleting `--scope change` and folding
slop findings on the diff into a `code-review` lens (b), taking the chain from
nine stages to eight.

Resolved to **(a)** because the approval was given to a plan body written for
(a): Task 4 changes prose and adds a suite, and (b) was stated in the same
paragraph as adding two tasks and touching `workflow.md`'s stage table,
`test_workflow_contract.py` and `test_process_router.py`'s handoff walk. An
approval cannot be read as choosing the option the approved body does not
contain. **(b) remains a live option** and belongs in its own unit — removing a
numbered stage is a change to the chain, not to this gate.

None open.

## File map

| Path | Disposition | Owns afterwards |
|---|---|---|
| `tools/security_gate.py` | Create | the five clauses, `evaluate`, `gather_facts`, `render`, exit codes |
| `tools/test_security_gate.py` | Create | one assertion per clause, each proven by inverting that clause alone |
| `.claude/project-checks.json` | Modify | the `audit`-kind entry and the `test_map` row |
| `tools/delivery_check.py` | Modify | a `security` finding, so `delivering` refuses a branch the gate blocks |
| `tools/test_delivery_check.py` | Modify | coverage for that finding, including its `unknown` path |
| `.claude/skills/code-review/SKILL.md` | Modify | lens selection computed from the gate rather than judged |
| `.claude/commands/plan-review.md` | Modify | the correct path to the artifact-review reference |
| `.claude/commands/wip.md` | Modify | absorbs `/git-state`'s counts section |
| `.claude/commands/git-state.md` | Delete | — folded into `/wip` |
| `tools/test_referenced_paths.py` | Modify | `BUILTIN_COMMANDS` without `/git-state` |
| `CLAUDE.md` | Modify | the command list and the safety-rail table |
| `.claude/workflow.md` | Modify | the safety-rails table gains the gate |
| `tools/README.md` | Modify | the tool index |
| `docs/plans/2026-08-11-security-gate.md` | Modify | this plan — `executing-plans` ticks its own `## Progress` boxes, so the plan is a path the work touches |

## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [x] Task 1 — the gate: clauses, seam and CLI
- [x] Task 2 — wire into the audit kind and the test map
- [x] Task 3 — wire into delivery_check
- [x] Task 4 — code-review's lens selection becomes computed
- [x] Task 5 — the dangling artifact-review reference
- [x] Task 6 — fold /git-state into /wip
- [x] Task 7 — documentation

## Tasks

### Task 1: The gate — clauses, seam and CLI

**Purpose:** `evaluate(facts)` returns one finding per fired clause and a finding
of severity `unknown` for every clause whose input was `None`; `python
tools/security_gate.py --base <ref>` gathers those facts and exits `0`/`1`/`2`.

One task and not two because the pure/IO split is a division inside one file:
a reviewer cannot accept the evaluator and reject the seam separately, and a
second task declaring `Modify: tools/security_gate.py` would name a path that
does not exist when the plan is read.

**Files:**
- Create: `tools/security_gate.py` — `CLAUSES`, `WATCHED_TABLES`, `ALLOW_RE`, `evaluate`, `exit_code`, `gather_facts`, `render`, `main`
- Test: `tools/test_security_gate.py` — one case per clause, each inverted alone, plus an `offline=True` case

**Dependencies:** none

**Implementation notes:**
- `facts` keys: `removed_table_entries: dict[str, list[str]] | None`,
  `added_lines: list[str] | None`, `changed_paths: list[str] | None`,
  `test_map: dict | None`, `agents: list[dict] | None`, `deps_exit: int | None`,
  `allows: set[str]`. Any `None` yields `unknown` for that clause and nothing
  else — never absent, never a pass, mirroring `delivery_check.unknown()`.
- `exit_code`: `1` if any `blocking`, else `2` if any `unknown`, else `0`. Copy
  the docstring rationale from `delivery_check.exit_code`.
- `ALLOW_RE = re.compile(r"#\s*security-gate:\s*allow\s+([a-z-]+)\s*(?:—|--)\s*(.+)")`
  — a clause named with no reason after the dash does **not** suppress; an
  allow with no reason is the boilerplate this repo refuses elsewhere.
- Secret matching reuses `_hooklib.SECRET_PATTERNS` through
  `importlib.util.spec_from_file_location`, exactly as `scope._migration_patterns`
  does. No copy of the list appears in this file.
- `agent-unscoped` reads each agent dict's `tools` and `allowed_paths` keys,
  parsed from the agent front-matter by `gather_facts`.

Then the seam, which is the only place a subprocess is called:

- `git show <base>:<path>` and the working copy give the two revisions;
  `ast.parse` + `ast.literal_eval` extract each watched table's literal. A table
  that cannot be parsed at either revision is `None` for that entry, never an
  empty list — an unreadable table reporting "nothing removed" is the silent
  degradation this whole file exists to prevent.
- `.claude/project-checks.json` is compared as JSON, not as text: a key whose
  value is `false` at head and was not at base counts as a removed entry under
  the pseudo-table name `project-checks`.
- `added_lines` from `git diff --unified=0 <base>...HEAD`, taking only `+` lines
  and excluding the diff header. `...` and not `..` — the branch against its
  merge base, matching what `delivery_check` calls `base-alignment`.
- `deps_exit` runs `python tools/deps.py` only when `changed_paths` includes
  `pyproject.toml` or a lockfile; otherwise the clause is not considered at all
  rather than reported as passing.
- `--json` for machine use, mirroring `scope.py` and `delivery_check.py`.
- `offline=True` skips every subprocess and returns `None` for every fact, which
  is what makes the suite hermetic.

**Rollback:** delete both files; nothing imports them until Task 2.

**Preconditions:** `tools/scope.py` still exposes `SENSITIVE_PATTERNS` and
`CONTROL_PATTERNS` as module-level list literals — `ast.literal_eval` depends
on it.

**Verification:**
- Run: `python tools/test_security_gate.py && PYTHONIOENCODING=utf-8 python tools/security_gate.py --base main`
- Expect: the suite exits 0 printing one `OK:` line per clause, each proven red
  first by inverting only that clause's fact; the CLI exits 0 on this branch
  printing `security-gate: clean -- 5 clause(s) evaluated, 0 fired`, and exits 2
  with every clause named `NOT EVALUATED` under `--offline`.

**Done when:** every clause has a passing case, a failing case and a `None` case
that produces `unknown` rather than a pass, and the CLI produces all three exit
codes on demand.

### Task 2: Wire into the audit kind and the test map

**Purpose:** `run_checks.py --tier all` runs the gate, and a change to
`tools/security_gate.py` selects its own suite under `--scoped`.

**Files:**
- Modify: `.claude/project-checks.json:audit` — append `python tools/security_gate.py --base main`
- Modify: `.claude/project-checks.json:test` — append `python tools/test_security_gate.py`
- Modify: `.claude/project-checks.json:test_map` — `tools/security_gate.py` → `python tools/test_security_gate.py`
- Modify: `.claude/project-checks.json` — a `_why_security_gate` note, in the style of the existing `_why_` keys

**Dependencies:** 1

**Implementation notes:**
- The `audit` kind and not `lint`: it reads git blobs and may shell out to
  `deps.py`, and the fast tier gates every auto-commit.
- `--base main` is written explicitly rather than defaulted. `tools/worktree.py`
  made the same call for the same reason — the default is the bug.
- CI needs no edit: `.github/workflows/checks.yml` calls the same resolver, which
  is why local and CI cannot drift.

**Rollback:** remove the three lines from `.claude/project-checks.json`; the tool
stays and simply is not called.

**Preconditions:** the gate exits 0 on this branch, or adding it to the tier
turns the repository red on landing.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS`, with the check count one higher than the run before this task
  and `audit` among the named kinds.

**Done when:** `python tools/test_project_checks.py` exits 0 and the full tier
names the gate.

### Task 3: Wire into delivery_check

**Purpose:** `delivering` cannot report a branch ready while the gate blocks it.

**Files:**
- Modify: `tools/delivery_check.py:gather_facts` — a `security` fact from the gate's `--json`
- Modify: `tools/delivery_check.py:evaluate` — a `security` finding, `unknown` when the fact is `None`
- Test: `tools/test_delivery_check.py` — a blocking case, a clean case, and the `None` case

**Dependencies:** 1

**Implementation notes:**
- Import `security_gate` rather than shelling out to it: both are `tools/`
  modules and a subprocess here would double the git work already done.
- The finding's text names the fired clauses, not a count — `delivery_check`'s
  existing findings all name the fact that fired.
- Keep the existing `exit_code` contract: a blocking security clause is `1`, an
  unevaluated one is `2`.

**Rollback:** revert `tools/delivery_check.py`; its suite's three new cases go
with it.

**Preconditions:** Task 1 landed `--json`, which this consumes.

**Verification:**
- Run: `python tools/test_delivery_check.py`
- Expect: exits 0 with the three new assertions named in its output.

**Done when:** a fixture whose facts carry a blocking clause makes
`delivery_check` exit 1, and a fixture with `security: None` makes it exit 2.

### Task 4: code-review's lens selection becomes computed

**Purpose:** the security lens stops being loaded "when the diff earns it" and
starts being loaded when a clause fires.

**Files:**
- Modify: `.claude/skills/code-review/SKILL.md:Lenses` — a step running the gate, and the mandatory-lens rule
- Modify: `.claude/skills/no-slop/SKILL.md` — state the division against `code-review` explicitly, replacing the bare assertion

**Dependencies:** 1

**Implementation notes:**
- The lens table stays; what changes is the sentence above it. Step 2 of the
  skill already runs `tools/scope.py`; this adds `tools/security_gate.py --json`
  beside it, and a fired clause makes `references/security-review.md` mandatory
  rather than discretionary.
- The other three lenses remain judged by what changed. Making all four
  computed is not in this plan and would need clauses none of them have.
- `no-slop`'s change is prose only under resolution (a) of the open question
  above; if (b) is chosen this task is rewritten and two more are added.
- No skill gains a new trigger word, so the description budget is unchanged —
  `test_process_router.py` prints the running total and will show it flat.

**Rollback:** revert both `SKILL.md` files; the gate keeps running in the tier.

**Preconditions:** the open question above is resolved at Gate 1, because
resolution (b) rewrites this task.

**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exits 0, the gate set still reported as exactly two, and the printed
  description-budget total unchanged from the run before this task.

**Done when:** `code-review` names the command that decides its security lens,
and neither skill asserts a boundary it does not check.

### Task 5: The dangling artifact-review reference

**Purpose:** `/plan-review` stops instructing the session to invoke a skill that
has not existed since the consolidation.

**Files:**
- Modify: `.claude/commands/plan-review.md` — `artifact-review` → `.claude/skills/writing-plans/references/artifact-review.md`

**Dependencies:** none

**Implementation notes:**
- The same class of defect `test_referenced_paths.py` was written for, missed
  because that suite reads hooks and skills and not command bodies. Widening it
  to commands is the mechanism half and belongs here, not in a later sweep.
- Add commands to the suite's scanned set in the same task, or the fix is prose
  and Article VI is unmet.

**Rollback:** revert the two files.

**Preconditions:** none — this task is independent of every other.

**Verification:**
- Run: `python tools/test_referenced_paths.py`
- Expect: exits 0, and reverting only the `plan-review.md` line makes it exit 1
  naming that file.

**Done when:** the suite reads command bodies and fails on a skill name that
resolves to no skill directory.

### Task 6: Fold /git-state into /wip

**Purpose:** three read-only state reporters become two.

**Files:**
- Modify: `.claude/commands/wip.md` — a counts section carrying `/git-state`'s numbers-with-their-command discipline
- Delete: `.claude/commands/git-state.md`
- Modify: `tools/test_referenced_paths.py:BUILTIN_COMMANDS` — `/git-state` removed

**Dependencies:** 5

**Implementation notes:**
- `/git-state`'s own header spends two lines arguing it is not `/wip`. The
  content worth keeping is the discipline, not the separation: every number
  printed with the command that produced it.
- `/handoff` stays. It writes a durable artefact for the next session; the other
  two answer a question for this one.
- `tools/resume.py` and `session-start/03-state-report.py` are untouched — they
  are the engine and the injection, not commands.

**Rollback:** `git checkout <sha> -- .claude/commands/git-state.md` and revert
the other two files. Recovering the deleted file from git rather than rewriting
it is the working agreement.

**Preconditions:** Task 5 landed the widened `test_referenced_paths.py`, which
is what proves no document still points at `/git-state`.

**Verification:**
- Run: `python tools/test_referenced_paths.py && python tools/test_command_standards.py`
- Expect: both exit 0, the second reporting one fewer command contract than
  before.

**Done when:** no file in the repository references `/git-state` except `LOG.md`
and this plan, and `/wip` prints the counts.

### Task 7: Documentation

**Purpose:** the durable docs describe the layer that exists.

**Files:**
- Modify: `CLAUDE.md` — the command list loses `/git-state`; the safety-rail table gains `tools/security_gate.py`
- Modify: `.claude/workflow.md` — the 2026-08-11 safety-rails table gains a row
- Modify: `tools/README.md` — the tool index gains the gate

**Dependencies:** 2, 3, 4, 5, 6

**Implementation notes:**
- One row in each table, no restated counts. `CLAUDE.md` says "the twelve slash
  commands"; that number is now eleven and is exactly the kind of restated count
  this file's own history warns about — replace it with an unnumbered phrase
  rather than decrementing it.
- The receipt history belongs in this plan and in `LOG.md`, not in `CLAUDE.md`.

**Rollback:** revert the three files; no behaviour depends on them.

**Preconditions:** every earlier task has landed, so the documentation describes
a tree that exists.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS`, with `test_referenced_paths`, `test_no_slop --scope layer` and
  `test_process_router` all green against the edited docs.

**Done when:** no document names `/git-state`, and every document naming the
gate names its real path.

## Approved

2026-08-11, Gate 1, via `ExitPlanMode`. Seven tasks, risk `high`, schedulable as
`2 group(s) may run concurrently, 1 must not`. The open question above was
resolved to (a) by the approval itself; (b) is deferred to its own unit.

## Deviations, reconciled

**Task 1 — `ast.literal_eval` became `ast.unparse` per element.** The plan said
literal_eval reads the watched tables. It cannot: `SECRET_PATTERNS` is a list of
`re.compile(...)` *calls*, so there is no literal to evaluate. `table_entries`
unparses each element instead, which compares the same unit a reader would call
"an entry" and works for a list of expressions and a dict alike. `ast.unparse`
also normalises quote style, so reformatting a pattern does not read as removing
it — asserted in the suite rather than tolerated, because a clause that goes red
on `ruff format` gets switched off within a week.

**Task 1 — the module was written before its suite,** contrary to Article II.
Stated rather than papered over. Every clause is nonetheless proven by inverting
it alone, which is the property the article exists to buy, and the suite found
one defect in the module on its first run.

**Task 2 — one row added to `test_map` beyond what the plan declared:**
`.github/workflows/**` → `python tools/test_ci_shape.py`. Not scope creep but
the gate's own first finding: `checks.yml` matches `SENSITIVE_PATTERNS`, had
changed on this branch, and was mapped to no suite — while `test_ci_shape.py`
had existed and covered it all along. Leaving it would have meant landing a
check that was red on arrival.

**Task 1 — two defects the CLI found in itself on its first real run**, both
fixed and both covered:
- `subprocess.run(text=True)` decodes with the console encoding, so `git show`
  returned the emoji in `AI_ATTRIBUTION_PATTERNS` mojibaked while the head side
  was read as UTF-8. The two compared unequal and `control-weakened` reported a
  guard removed that nobody had touched — a false positive from a locale
  difference, in the exact class `CLAUDE.md`'s first gotcha names.
- `_agent_facts` was written and never called, so `agent-unscoped` reported
  `unknown` on every run. Exit 2 rather than a false pass, which is the shape
  Article V buys, but the clause had never once been evaluated.

**Task 5 — the gap was not where the plan said it was.** The plan had
`test_referenced_paths.py` widened "to read command bodies". It already read
them: `SOURCES` globs all of `.claude/**/*.md`. What it validated was paths,
`/commands`, env vars and symbols — never a bare backticked **skill name**,
which is the shape `artifact-review` had. The check added instead is mechanical
and keeps no list: a `<skill>/references/*.md` stem may be cited by path, and a
bare `` `stem` `` is a finding, with stems that are also a live skill or command
name excluded as genuinely ambiguous. It found five more instances of the same
defect on its first run — four reference files still handing work to
`test-driven-development` and `observability-sre` as though they were skills.
All five are repaired.

**Task 5 — one file beyond the declared set: `README.md`.** Adding a suite made
its "40 suites" claim false and `test_referenced_paths.py` red. Fixing the count
it broke is not scope creep; leaving it would have meant landing a red check.

**Task 6 — reverted, and the plan was wrong.** The plan folded `/git-state` into
`/wip` and deleted it, on the audit's finding that the repository has five
overlapping state reporters. Read in full, the two bodies barely overlap:
`/git-state` carries eight sections of counting — base-branch detection, the
four buckets and why they do not sum, status codes, what a bare commit would
take, recoverable refs, branch-name coherence — and `/wip` carries none of it,
while `/wip`'s staleness judgement appears nowhere in `/git-state`. The overlap
the audit saw was between their *descriptions*. Deleting the command would have
lost real content or grown `/wip` to 200 lines, and neither is what the audit
asked for.

What was actually duplicated is one line, and it hid a bug: `/wip` §1 asked for
"how far ahead of the base branch" while `/git-state` §1 exists partly to warn
that assuming `main` fails outright on a repository whose base is `master`.
`/wip` now points at `/git-state` for the detection and the counts, and keeps
the judging. `/git-state`, `BUILTIN_COMMANDS` and `CLAUDE.md`'s command list are
unchanged. Five reporters remain five; the honest count of duplicated content
was one line, not one command.

**Task 7 — two files beyond the declared set, both broken by earlier tasks.**
`README.md`'s "40 suites" became false when Task 1 added one, and
`.claude/skills/code-review/SKILL.md` and `no-slop/SKILL.md` carried dated
provenance ("until 2026-08-11") that `test_no_slop.py --scope portability`
correctly calls false in any other repository. Both are consequences of this
change, not new scope.

**The full tier found five failures the task-level checks did not.** Recorded
because each is a class worth knowing:
- `test_no_slop.py --scope layer`: `security_gate.py` spawned subprocesses
  without `stdin=subprocess.DEVNULL`. The symptom is not an error — it is the
  suite hanging, and only when run through the tier, because a hook inheriting
  an open pipe blocks in `load_payload()`. Both call sites fixed.
- `test_package.py`: the same defect again, from inside the built wheel. The
  slow tier is the only thing that runs the artefact rather than the source.
- `ruff`: `zip()` without `strict=`, and an import ruff wanted at module level.
- `mypy`: `ast.stmt` has no `.value`, so the node walk needed an explicit
  `else: continue`; and two test dicts needed annotations before `**` spreads
  typechecked.
- `--scope portability`: the dated claims above.

**Verified end to end, not only in fixtures.** Removing one real entry from
`_hooklib.SECRET_PATTERNS` and running the gate against `main`:

    [control-weakened] BLOCKING: 1 security control(s) hold fewer entries…
        .claude/hooks/_hooklib.py:SECRET_PATTERNS lost 1: re.compile('glpat-…')
    GATE EXIT=1

Adding `# security-gate: allow control-weakened -- proving the escape hatch end
to end` returned it to `exit 0`, and restoring the file returned it to `exit 0`
with the clause live again. The suite proves `evaluate`; this proves the whole
path from `git show` to the exit code.
