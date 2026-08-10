# Delivery Preflight Implementation Plan

**Goal:** one script that computes seven delivery facts about a branch and its
pull request, reports them, and refuses to decide.

**Source brief:** `TASK.md`, plus `docs/specs/2026-08-09-delivery-preflight-design.md`

**Slug:** delivery-check

**Architecture:** the shape every tool here already takes. `resume.py` derives
state from git, `analyze.py` takes an injected `exists()` so every branch is
reachable without building a repository, and `git_identity.py` splits IO
(`gather(root, offline=)`) from a pure `render()` and states outright that it
"ranks; it does not choose". `delivery_check.py` is the same: `gather_facts()`
does the IO behind an `offline` escape, `evaluate(facts)` is pure and is what the
tests drive, and nothing in it mutates a repository.

**Tech stack and constraints:** Python 3.11+, stdlib plus `git` and `gh`, no new
dependency. Windows-first (`PYTHONIOENCODING=utf-8` before any tool script).
Not in the fast tier — it needs a network and a remote, and that tier gates every
auto-commit in seconds.

## Why this is advisory and not a gate

    gh api repos/<owner>/<repo>/branches/main/protection
    → 403 Upgrade to GitHub Pro or make this repository public

Required checks, branch protection and merge queues are unavailable on a free
private repository. Nothing here can *prevent* a bad merge; it can only make the
facts undeniable before a human clicks. Building it as though it were a gate
would produce one that quietly does nothing, which is this repository's stated
worst failure mode.

**Whether to go public or upgrade to Pro is deliberately not a blocker here.**
It changes how much this is worth, not what gets built — the checks are identical
either way, and `enforcement` reports the 403 whichever answer comes. Recorded
under Risks instead of holding the gate.

## The two failures this exists to catch

Both happened on 2026-08-09, hours apart, and neither was caught by any suite:

1. **A PR opened with `--base X` from a branch cut off `Y`** showed ten files
   instead of three. Caught by a human reading the PR list.
2. **Merge order stranded three merged units.** A child merged upward before its
   siblings merged into it, so four PRs read "merged" while the work was absent
   from the branch heading for `main`. Caught by counting files during an
   unrelated question.

Check 1 below catches both. It is one command.

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `tools/delivery_check.py` | Create | `gather_facts()` (IO), `evaluate()` (pure), `render()`, `main()` |
| `tools/test_delivery_check.py` | Create | One assertion per check, each proved red first |
| `.claude/skills/delivering/SKILL.md` | Modify | Gains the step that runs and quotes it |
| `.claude/project-checks.json` | Modify | Only if it proves fast enough; otherwise untouched and said so |

## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [ ] Task 1 — `tools/delivery_check.py` and its suite
- [ ] Task 2 — `delivering` runs and quotes it

## Tasks

### Task 1: `tools/delivery_check.py` and its suite

**Purpose:** the script itself — a pure decision function, the IO behind a seam,
and a suite that drives every check without a repository or a network.

**Files:**
- Create: `tools/delivery_check.py` — `evaluate()` (pure), `gather_facts()` (IO), `render()`, `main()`
- Create: `tools/test_delivery_check.py` — one assertion per check, each proved red first

**Depends on:** none

**Implementation notes:**

*Written test-first within the task: `evaluate()` and its cases before any IO.*
The split is deliberate — one file, one task, because a task that modified a
file an earlier task created is a `Modify` target `analyze.py` cannot resolve,
and it said so.

- `evaluate(facts: dict) -> list[dict]`, each finding `{code, severity, finding}`
  with `severity` in `blocking` / `advisory` / `unknown`. No IO, so every case is
  a dict literal.
- The seven codes and the fact each reads:
  - `base-alignment` — `facts["merge_base"] == facts["base_tip"]`. **The one that
    catches both of today's failures.**
  - `ci` — `facts["ci"]` is `{"sha", "conclusion"}`; requires `conclusion ==
    "success"` **and** `sha == facts["head_sha"]`, because a run against an older
    SHA proves nothing about this tree.
  - `stack-depth` — advisory at 2, blocking at 4.
  - `merge-method` — `facts["merge_methods"]` against `facts["stack_depth"]`;
    squash enabled with a stack open is a finding.
  - `divergence` — a push needing `--force` is a finding naming
    `--force-with-lease`.
  - `worktree` — `facts["dirty"]` must be empty.
  - `enforcement` — `403` yields severity `unknown` and the words "advisory
    only", so a green result is never read as a guarantee.
- **A fact that is `None` yields `unknown`, never a pass.** Absent and passing
  are different answers.
- `gather_facts(root, base, head, offline=False)`; `offline=True` returns every
  network-derived fact as `None`, the escape `git_identity.gather(root,
  offline=)` already establishes. Subprocess helper in the shape of
  `git_identity._run`: `capture_output`, `stdin=DEVNULL`, `timeout`, `""` on
  `OSError`/`SubprocessError`. Never `shell=True` — `ruff` selects `S`.
- `gh` absent, unauthenticated or answering `403` is not a crash: the fact
  becomes `None`.
- Exit codes: `0` no blocking findings · `1` at least one blocking · `2` any fact
  `None`, naming which and why.

**Resolved at Gate 1 — blocking, with an explicit `--allow-pending`.** This is
what a required status check does: GitHub treats *expected but not reported* as
unsatisfied and blocks, and every real system pairs that with an explicit
override rather than an implicit one. Pending and failing are both "not proven
green"; the difference is only how long you wait. `--allow-pending` downgrades
`ci` to advisory for one run and says so in the output, so proceeding is a thing
somebody typed.

**Resolved at Gate 1 — squash, and never stack.** Squash-merge onto short-lived
independent branches is the dominant trunk-based convention, and it is what this
repository already assumed: `CLAUDE.md` says `wip:` checkpoints are deliberate
*because* squash collapses them. It also removes today's failure at the source —
a stack cannot be stranded by merge order if there is no stack.

So `merge-method` compares against a declared intent of `squash`, and its finding
is: **squash enabled while more than one PR chains to the default branch.** That
is the incompatible combination, and it is blocking rather than advisory, because
it is precisely what stranded three merged units.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_delivery_check.py && PYTHONIOENCODING=utf-8 python tools/delivery_check.py --offline`
- Expect: the suite exits 0 with one `OK:` per check; the offline run exits 2 and
  names every undetermined fact

**Done when:** inverting any one fact turns exactly that check red, and the
offline run reports `unknown` by name rather than passing.

### Task 2: `delivering` runs and quotes it

**Purpose:** the check is worthless if nothing invokes it; `delivering` must not
report `clean` without quoting it.

**Files:**
- Modify: `.claude/skills/delivering/SKILL.md` — a numbered step plus the reason
- Modify: `tools/test_process_router.py` — assert the skill names the script

**Depends on:** 1

**Implementation notes:**
- One step in `## Steps`, before the push confirmation: run it, quote the output,
  treat exit `1` as a stop rather than a note.
- Prose stays as the *reason* beside the mechanism, never as the mechanism —
  `delivering` already said "confirm the base is known" and the wrong base was
  declared anyway, by an agent that had read the file that morning.
- The assertion goes beside the existing `OUTWARD_SKILLS` block, which already
  checks this skill for its `AskUserQuestion` and its prose-question rule.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 36 check(s) green (audit, build, lint, smoke, test, typecheck)`

**Done when:** `delivering` names the script, the suite asserts it, and the full
tier is green.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Task 1 is the pure function and its tests before any IO
- [x] III Smallest change — two new files, two edits, no refactor
- [x] IV Reversibility — the script mutates nothing; it reads and reports
- [x] V No silent degradation — exit `2` for undetermined, never folded into `0`
- [x] VI Mechanism — the checks are the mechanism; Task 3 asserts it is invoked
- [x] VII Secrets — no credential enters the repo

## Complexity tracking

No unticked boxes.

## Risks

- **Advisory by construction.** On this plan tier nothing prevents a merge, so
  the check's whole value rests on `delivering` running it. Task 3 is therefore
  not optional polish — it is the half that makes the other two matter.
- **`gh` availability varies.** Absent or unauthenticated `gh` degrades three
  checks to `unknown`. Correct, and it means a green run on a machine without
  `gh` proves less than it appears to. The report must say which.
- **The check that would have caught today's failures is one line.** The risk is
  reading that as sufficient: the other six are unproven against real incidents,
  and a green sweep is evidence the checks bite, never that coverage is complete.

- **Enforcement is unavailable, and that is not this plan's to fix.** Branch
  protection and merge queue answer `403` on a free private repository. Going
  public or upgrading to Pro would turn every check here from advisory into
  enforced. Worth revisiting; it changes the value of this work, not its shape.

## Approved

2026-08-10. Gate 1 passed. `ci` pending resolved as blocking with an explicit
`--allow-pending`; merge method resolved as squash with no stacking; the
public/Pro question demoted from a marker to a risk because it does not change
what gets built.
