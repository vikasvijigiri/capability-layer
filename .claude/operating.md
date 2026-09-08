# Operating detail

Moved out of `CLAUDE.md` on 2026-08-12, which loads every session; this does
not. Moved out of `workflow.md` in the same hour, for a reason worth keeping:
`test_process_router.py` reads **every backticked lowercase word in
`workflow.md` as a skill name**, so a table mentioning branch names and build
tools turned nine of them into dead skill references. The rules below are
unchanged; only where they are paid for is.


## The commit loop

Commits are automatic and local. `stop-finalization/06-artifact-autocommit.py` fires at
the end of every turn and commits what changed as a `wip:` checkpoint, if and
only if all of these hold. What "the checks pass" means is
`.claude/project-checks.json` resolved by `.claude/hooks/_projectchecks.py` — the
same code `/verify` calls, so the two cannot disagree:

| Gate | Refuses when |
|---|---|
| branch | on `main`/`master`/`develop`/`release` |
| size | more than `DEFAULT_MAX_FILES = 25` changed — a unit of work, not a checkpoint |
| secrets | any changed file matches `_hooklib.SECRET_PATTERNS` |
| checks | any **fast-tier** command exits non-zero |
| unverified code | the change contains code and **no test check ran** |
| migration | the change touches `_hooklib.MIGRATION_PATH_PATTERNS` |
| minimal diff | a changed path is named by neither `TASK.md` nor any `docs/plans/*.md` — **and the refusal prints those paths** |
| message | the generated subject matches `_hooklib.AI_ATTRIBUTION_PATTERNS` |

**Minimal means "no unrelated file", not "few lines".** It refuses rather than
warns, because a lone warning among seven refusals is the clause nobody reads.
The accepted cost is real — a turn touching an unplanned file gets no checkpoint
— which is why the refusal names the paths. The gate applies only where a
declaration source exists.

Every clause is a fact about the artefact, never about process. A refusal is
always spoken. It **never pushes**, never `git add .`.

Two dependencies, both easy to break:

- `UAIOS_AUTOCOMMIT_RUNNING` guards re-entry. Without it the hook runs the suites
  which run the hook, unbounded — presenting as a hang, not an error.
- Its commits **bypass `PreToolUse`**, so the secret and attribution checks run
  *inline* from `_hooklib`.

**`permission-security/02-branch-guard.py` resolves the command's target repo, not the
session's** — `git -C ../other commit` commits somewhere else. Both hooks use
`_hooklib.is_git_commit`, a tokeniser rather than a regex, because `-C` takes a
value and no regex repetition can consume it.

Checks come in **two tiers**, because cost differs by an order of magnitude and a
gate nobody can afford to run gets switched off:

| Tier | Kinds | Runs | Gates |
|---|---|---|---|
| fast | lint · typecheck · test | every turn, seconds | the auto-commit |
| slow | build · audit · e2e · smoke | before delivery, minutes | push / PR, and CI |

The slow tier (`python tools/run_checks.py --tier all`) runs **once per unit of
work, at delivery** — never per task and never mid-chain; mid-chain
verification is `--scoped` only.

`--scoped` narrows the fast tier on a `small` change and refuses a `major` one.
**"Fast" means *ran fewer checks and said which*, never *green on less
evidence*** — the three rules keeping that true are in `.claude/workflow.md`,
which owns the scope table.

**Review moves to the push/PR**, over the whole branch — a commit needing a human
is not a checkpoint.

## When the checks go red

`06-artifact-autocommit.py` writes the failing output to
`.claude/hooks/state/check-failure-report.md`, counts consecutive failures of the
*same* failure (digits normalised), and names `systematic-debugging`. It
**suggests**, never triggers — a hook cannot invoke a skill — and never blocks.

**The budget depends on the kind**, decided by `_hooklib.FAILURE_CLASSES` before
anything is spent: `security` 0, `transient` 2, `merge` 2,
`deterministic`/`unknown` 3. Unmatched output is a defect, never noise.
`tools/loop.py` turns class + attempt into one of six rungs (retry, repair,
restore, rebase, retreat, block); `test_loop.py` proves by exhaustion that every
path terminates. **`restore` is load-bearing** — three failed repairs leave the
tree worse than they found it. Green updates `refs/uaios/green/<slug>`; restore
goes there.

Green closes the loop **forward**: `verifying-work` → `code-review` →
`delivering`, so "no longer failing" is not mistaken for "finished".

**The slow tier is the only thing that verifies the running system.** Everything
else reads the source. `tools/smoke.py` starts the app, waits, probes and tears
the process tree down.

Detection is a data table (`MARKER_CHECKS`) covering Node, Deno, Python, Rust,
Go, Java, Kotlin, Ruby, PHP, Elixir, .NET and `make`; a new ecosystem is a row.
`.claude/project-checks.json` overrides any of it, `false` disables a kind as a
stated decision, and a configured tool that is not installed is **skipped and
named**, never failed.

---

## Gotchas

- **Set `PYTHONIOENCODING=utf-8` before running any tool script.** Several print
  `→` and `—`; the Windows console default raises `UnicodeEncodeError` and turns
  a passing run into a fake failure.
- **A hook bug's symptom is silence** — identical to "no problem". After editing
  any hook, fire it with `tools/run_hook.py` against a realistic payload.
- Hook scripts read input via `_hooklib.load_payload()`, so both stdin and
  `HOOK_PAYLOAD` work.
- **A skill is silently invisible** if it is a flat `.md` rather than
  `<name>/SKILL.md`, or if its frontmatter `name:` differs from its directory.
  Nothing errors — it just never appears.
- **Never use a per-process `hash()` where a value must be stable across runs.**
  It is SipHash-seeded per process; `chain.py` fingerprinted the tree that way
  and its stall detector's third limb was dead for its whole life.
- The `github` MCP server needs `GITHUB_TOKEN`. `gh` itself is already
  authenticated on this machine.
- **An unquoted `Word:` inside a skill's `description:` breaks YAML**, even
  though `new_skill_check.py`'s naive line-partition parser won't catch it —
  only a real YAML load (`test_process_router.py`) does. Write "Triggers
  include X" or quote the whole field; never a bare "Triggers: X".
- **A plan task's `**Files:**` block: every backticked token in it is read
  as a declared file**, not just the actual `- Create:`/`- Modify:` path —
  `tools/parallel_groups.py`'s parser scans the whole field for `` `...` ``,
  not just the leading bullet. An illustrative filename mentioned in prose
  inside that block (e.g. listing what a SCAN phase greps for) gets treated
  as a file this task writes, which can force a false shared-surface
  serialization. Keep such lists out of the `Files:` block — put them in
  `Implementation notes:` instead, without backticks if they resemble a
  real path.
- **Adding or removing a skill or agent moves a count duplicated in at
  least five places**, none of which cross-check each other: `README.md`,
  `.claude/README.md` (says "capabilities," now aliased to the same
  "skills" inventory in `test_referenced_paths.py`'s `NOUN_ALIASES`, fixed
  live after it let a stale count through once), `MEMORY.md`,
  `tools/test_layer_comparison_contract.py`'s hardcoded literal, and
  `docs/evals/trigger-queries.json`'s total (surfaced only by `python
  tools/eval_triggers.py --list`, which also refuses to run for a skill
  with no query set at all). Four of five are mechanically checked by
  `test_referenced_paths.py`; the fifth (`test_layer_comparison_contract.py`'s
  literal `!= N`) is deliberate — a frozen historical report it compares
  against must not be silently rewritten to match — so bump that one by
  hand and leave the report's own dated claim alone.

---

## Gate policy and subagent dispatch

Moved from `CLAUDE.md` on 2026-08-12. Unchanged; it is chain policy and this
file owns the chain. `.claude/policies/` is the companion by-purpose index —
`budgets.md`, `escalation.md`, `permissions.md`, `security.md`, each a pointer
to the instrument that enforces one gate; `.claude/workflow.md`'s safety-rails
table is the same set cut by what each tool refuses.

**Exactly two approval gates, each with its own tool.** Gate 1 is
`ExitPlanMode` (the finished plan); Gate 2 is `AskUserQuestion` (shipment, in
`release-git`'s releasing procedure). Neither is ever asked in prose — a prose question is answerable by
silence and scrolls away. Each declares itself with a `<!-- GATE n: ... -->`
marker, and `test_process_router.py` pins the set to two, checking each against
*its own* tool. Open questions are `[NEEDS CLARIFICATION]` markers resolved
together at Gate 1, never separate blocking asks. A rejection is durable: it
appends `## Rejected <date> (plan <hash>)` plus the user's words verbatim, and
`loop.py` refuses to re-present an unchanged body, retreating at three.

Delivery approval is separate and not counted: unapproved push, merge and deploy
are forbidden outright below.

### Subagents

Concurrent dispatch of a schedulable multi-task round is the **default and
required**, done by the skill owning the stage. The user does not ask for it; a
user may opt OUT and force serial, but opt-out is the exception. The real
constraints stay: parallel agents work only on **disjoint declared file sets**
and read-only review surfaces; shared interfaces, lockfiles, migrations and
release config are **serialized**; each task gets its own worktree and branch;
the whole round is **verified before the next round is dispatched**. Two
implementers may run at once when their file sets are disjoint — that is the
point of `tools/parallel_groups.py`.

**This "required" is `implementation` executing a `parallel_groups.py`-scheduled
plan.** A judgement-driven fan-out — `debugging` splitting unrelated failures,
`research` fanning out over sources — stays discretionary and each of those
skills says so ("only when the user has asked for subagents"); they climb the
context ladder first.

`Explore.md` overrides the built-in to pin haiku. `.claude/workflow.md` carries
the table; `test_process_router.py` asserts each agent has a "do NOT use"
clause, a `tools:` allowlist, a pinned model, and a dispatcher that names it —
and that it names its dispatcher back.

