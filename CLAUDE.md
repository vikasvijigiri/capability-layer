# CLAUDE.md

A Claude Code capability layer: skills, lifecycle hooks and slash commands that
enforce a spec → plan → build → verify workflow, plus the knowledge docs that
carry state between sessions. There is no application code here.

This file is a bootloader: point at the thing that owns the work rather than
restating it. History belongs in `LOG.md` and git.

Keep it roughly this length. There is no enforced ceiling any more: a hard number
turned every real addition into a hunt for lines to delete elsewhere, which is
editing by budget rather than by judgement. The cost is real and unchanged —
this file loads every session — so prefer a pointer to a paragraph, and put
history in `LOG.md`.

---

## Working agreement

- **Validate, don't assume.** Never report a check as passing unless you ran it
  and can quote its output.
- **Reuse before creating.** Recover a deleted file from git rather than
  rewriting it from memory.
- **Be terse.** Cap skill and command responses at ~500 tokens.
- **Prefer deterministic mechanisms** — a hook or a test over a written rule.

---

## Skills

In `.claude/skills/<name>/SKILL.md`. Each states its own triggers, gates and
handoffs — read the skill, don't infer an order from this list.

**`.claude/workflow.md` owns the order**: which skill owns which stage, what each
consumes and produces, and the two shapes (linear and loop). Read it before
adding a skill or wondering what comes next.

**The chain has exactly two workflow approval gates** — the finished plan at the
end of `writing-plans`, and the sign-off in `code-review`. Operational safety
checks may still require confirmation, such as choosing a worktree or target;
they do not grant approval to bypass either gate.
`tools/test_process_router.py` fails if a tenth skill grows a dialogue. Delivery is
separate and not counted: `delivering` and `releasing` still need an explicit yes,
because unapproved push, merge and deploy are forbidden outright below.

| Skill | Stage | Produces |
|---|---|---|
| `task-brief` | 1 frame | `TASK.md` — six fields, inferred ones marked |
| `brainstormer` | 2 design | `docs/specs/YYYY-MM-DD-<topic>-design.md` |
| `writing-plans` | 3 plan | `docs/plans/YYYY-MM-DD-<feature>.md` |
| `executing-plans` | 4 execute | the thing itself; ticked plan checkboxes |
| `verifying-work` | 5 validate | coverage verdict + the unbacked set |
| `no-slop` | 6 sweep | repo-wide findings; local repairs applied, structural reported |
| `code-review` | 7 review | findings + a sign-off receipt |
| `delivering` | 8 deliver | merged / pushed / PR opened |
| `releasing` | 9 release | the change serving at a named target + a quoted smoke check |
| `knowledge-manager` | 10 record | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `decisions/` |
| `research` | — entered from any stage | `docs/research/YYYY-MM-DD-<topic>.md` |
| `systematic-debugging` | — entered on any failure | root cause + `ISSUES.md` entry |
| `capability-layer-maintenance` | — entered to change this layer | aligned contracts, wiring, hooks, and green validators |
| references | each stage keeps its depth in `<skill>/references/` — review lenses, worktrees, TDD, artifact review, design contract, SRE | loaded per task, not per turn |

**Skills trigger from their own `description:` frontmatter, and nothing else.**
A `UserPromptSubmit` hook and a `routing/process-skills.md` keyword table were
deleted on 2026-08-04. A hook whose only output is the name of a skill couples two
independent things and duplicates a routing decision nothing validated -- pointing
one at a fabricated skill was tried, and every suite passed. The cost of removing
it is real: there is no second signal when a description misses a phrasing.

### Subagents

Dispatched by the skill that owns the stage, only when the user has asked for
subagents. `Explore.md` is different: it overrides the built-in to pin haiku.

`source-digger` (research), `failure-investigator` (debugging),
`diff-reviewer` (review), `spec-reviewer` (spec compliance), `test-verifier`
(verification), `architecture-reviewer` (design), `security-reviewer` (security),
and `release-verifier` (release evidence) fan out; `task-implementer` **never
runs two at once**.
`.claude/workflow.md` carries the table. `tools/test_process_router.py` asserts
each has a "do NOT use" clause, a `tools:` allowlist, a pinned model, and a
dispatcher that names it — and that it names its dispatcher back.

`tools/test_process_router.py` asserts the skill and agent layer resolves against
itself: frontmatter parses, names match directories, every skill named in prose
exists, and each chain skill states its successor imperatively.

---

## Model and effort budget

Every skill declared `model: opus` + `effort: high` until 2026-08-02 — a default
nobody revisited, and it applied on every turn. The policy now:

`opus` for planning and diagnosis, `sonnet` for coding and procedure, `haiku`
for pure extraction — the per-skill values are in each `SKILL.md` frontmatter,
which is the source of truth. `effort` tracks the same axis.
`systematic-debugging` keeps `opus` though diagnosis is not planning: three
2026-08-02 bugs were caught in reasoning alone and were invisible in the diff.

Two other levers: **`/fast`** (same Opus 5, less extended thinking — right for
doc sweeps and bulk edits, wrong for debugging), and **request shape**, which is
the biggest and is the user's. Deliberation goes on resolving ambiguity, not
solving problems; one goal per request cuts it directly.

Descriptions are injected **every turn** and are the only trigger surface, so
breadth is paid for there. `tools/test_process_router.py` prints the running
total; it measured 7,813 chars before the 2026-08-07 tightening, and is smaller
now because framing was cut and four audit skills became `code-review` lenses. Every one carries a
`Do NOT use` clause, and two checkers fail without it.
`session-start/02-bootstrap-docs.py` is budgeted for the same reason: it injected
26,990 chars before anyone typed, and now clips to ~5,500.

---

## Commands

    /verify          canonical full lint, test, typecheck and capability checks
    /verify-change   fast checks for the current change
    /save            explicitly confirmed local commit; never pushes
    /wip             branch, uncommitted work, and documentation staleness
    /git-state       exact Git counts and branch accounting
    /skills-doctor   deterministic capability-layer diagnosis
    /plan-review     independent spec/plan review before execution
    /security-review independent trust-boundary review
    /release-check   non-destructive release-readiness evidence
    /handoff         durable read-only session-state report
    /pr-review       high-confidence pull-request review; local by default

Raw equivalents, run from the repo root:

    python tools/run_checks.py --tier all --require-test   # both tiers
    python tools/resume.py            # which state this unit of work is in
    python tools/analyze.py           # is the plan internally consistent (pre-Gate 1)
    python tools/loop.py              # what the escalation ladder says to do next
    python tools/loop.py --restore    # reset to the last verified-green tree
    python tools/new_skill_check.py <name>|--all   # is one skill actually reachable
    python tools/smoke.py --url <url> --expect-status 200   # is it actually serving
    python tools/run_hook.py <event> '<json-payload>'   # fire one hook manually

Individual suites live in `.claude/project-checks.json` — the copy that sat here
named seven of nineteen. Run `/verify` before declaring any work done.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | the 13 skills above, one directory each; `<skill>/references/` holds depth loaded on demand, not per turn |
| `.claude/agents/` | ten agents: the fan-out set dispatched by skills, plus `Explore` overriding the built-in onto haiku |
| `.claude/workflow.md` | stage → owning skill → artefact; the chain and its invariants |
| `.claude/hooks/<event>/` | hooks over several events that act, deny or measure; `session-start`, `post-run`, `pre-commit`, `pre-edit`, `pre-deploy`, `on-artifact-create` |
| `.claude/settings.json` | what actually fires for this repository; `hooks_registry.json` documents the repository's hook contract |
| `.claude/commands/` | the eleven slash commands above |
| `tools/` | `run_checks.py` (one entry point for green), `resume.py` (where this unit of work is), `loop.py` (the escalation ladder), `smoke.py`, `run_hook.py`, the suites |
| `docs/specs/`, `docs/plans/`, `docs/research/` | skill outputs, one dated file each |
| `docs/archive/` | the pre-2026-08-01 design layer; superseded, see `docs/archive/ARCHIVE.md` |
| `decisions/` | dated ADRs |
| `.claude/skills/releasing/references/` | platform packs — deploy/smoke/rollback per target |
| `.github/workflows/checks.yml` | CI; calls the same resolver, so it cannot drift from local |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

`~/.claude/` holds no skills or agents. `session-start/02-bootstrap-docs.py`
initialises scaffolding in place; nothing copies the layer into other repos.

**`../physrun/` is a sibling repo, not part of this one** — the first product
built with this layer, and the first test of whether it ports. Copying this file
wholesale would be wrong: it asserts "there is no application code here" and a
hook count, both false there. Porting found three bugs in a day, none findable
from inside this repo. See `LOG.md` 2026-08-03 14:30.

---

## Knowledge docs

Six files at the repo root carry state between sessions. Hooks read and gate on
them, so they are code, not commentary:

`TASK.md` (active task) · `HANDOFF.md` (current work, pending, next)
· `LOG.md` (history) · `ISSUES.md` · `MEMORY.md` · `README.md`

**`session-start/03-state-report.py` measures them.** It counts commits since
`LOG.md`/`HANDOFF.md`/`ISSUES.md` last changed, and `.claude/` files changed since
the branch point, then renders the matching `[state:<key>]` block from
`.claude/workflow.md`. It names no skill — workflow.md decides what a state means,
and `tools/test_hook_registration.py` fails if any hook names one. Measured
against git alone, so there is no counter to clear.

## The commit loop

Commits are automatic and local. `post-run/06-artifact-autocommit.py` fires at
the end of every turn and commits what changed, as a `wip:` checkpoint, if and
only if all six hold. What "the checks pass" means is `.claude/project-checks.json`
resolved over detection by `.claude/hooks/_projectchecks.py` — the same code
`/verify` calls, so the two can never disagree:

| Gate | Refuses when |
|---|---|
| branch | on `main`/`master`/`develop`/`release` |
| size | more than `MAX_FILES = 25` changed — that is a unit of work, not a checkpoint |
| secrets | any changed file matches `_hooklib.SECRET_PATTERNS` |
| checks | any **fast-tier** command exits non-zero — lint, typecheck, test |
| unverified code | the change contains code and **no test check ran** — passing and having nothing to run are different facts |
| migration | the change touches `_hooklib.MIGRATION_PATH_PATTERNS` — the least reversible thing here, and no suite proves it |
| message | the generated subject matches `_hooklib.AI_ATTRIBUTION_PATTERNS` |

Every clause is a fact about the artefact, never about process. A refusal is
always spoken. It **never pushes**, never `git add .`.

Checks come in **two tiers**, because cost differs by an order of magnitude and a
gate nobody can afford to run gets switched off:

| Tier | Kinds | Runs | Gates |
|---|---|---|---|
| fast | lint · typecheck · test | every turn, seconds | the auto-commit |
| slow | build · audit · e2e · smoke | before delivery, minutes | push / PR, and CI |

    python tools/run_checks.py --tier all --require-test

**Review moves to the push/PR**, over the whole branch — a commit that needs a
human is not a checkpoint. `wip:` is deliberate: squash-merge collapses them.

Two things this depends on, both easy to break:

- `UAIOS_AUTOCOMMIT_RUNNING` guards re-entry. `tools/test_hooks.py` fires the
  whole `post-run` event, so without it the hook runs the suites which run the
  hook, unbounded — presenting as a hang, not an error.
- Its commits **bypass `PreToolUse`**, so the secret and attribution checks run
  *inline* from `_hooklib`; `pre-commit/01-secret-scan.py` never sees them.

**`pre-commit/02-branch-guard.py` resolves the command's target repo, not the
session's.** `cd ../other && git commit` and `git -C ../other commit` both commit
somewhere else, and until 2026-08-03 the guard read *this* repo's branch and let
eight commits onto a sibling's protected `main` — silently. Both hooks now use
`_hooklib.is_git_commit`, a tokeniser rather than a regex, because `-C` takes a
value and no regex repetition can consume it. See `ISSUES.md` 2026-08-03 14:20.

Nineteen hooks were deleted on 2026-08-02, including every process-compliance
gate and the staging guards. Why, and the deadlock that proved it: `LOG.md`
2026-08-02 19:26 / 21:30, and `docs/2026-08-02-git-flow-walkthrough.md`.

## When the checks go red

The refusal is not the end of the message. `06-artifact-autocommit.py` writes
the failing output to `.claude/hooks/state/check-failure-report.md`, counts
consecutive failures of the *same* failure (digits normalised, so a partial fix
does not reset the budget), and names `systematic-debugging` — whose stated
trigger a failing check is.

It **suggests**, never triggers: a hook cannot invoke a skill, confirmed in the
official docs. And it never blocks — `post-run/05-docs-gate.py` blocked a turn
until a skill ran, deadlocked, and was deleted on 2026-08-02.

**The budget depends on the kind**, decided by `_hooklib.FAILURE_CLASSES` — a
table, not a judgement — before anything is spent: `security` 0, `transient` 2,
`merge` 2, `deterministic`/`unknown` 3. Unmatched output is a defect, never
noise. Until 2026-08-07 every red check cost the same three attempts, so a locked
file escalated like a type error, and "repairing" it meant editing product code
to chase a fault that was not in it. `tools/loop.py` turns class + attempt into
one of six rungs (retry, repair, restore, rebase, retreat, block); `test_loop.py`
proves by exhaustion that every path terminates. **`restore` is load-bearing** —
three failed repairs leave the tree worse than they found it, so a fourth debugs
the loop's own damage. Green updates `refs/uaios/green/<slug>`; restore goes
there.

Green closes the loop **forward**: `verifying-work` → `code-review` →
`delivering`, so "no longer failing" is not mistaken for "finished".

**The slow tier is the only thing that verifies the running system.** Everything
else reads the source. A repo can lint, typecheck and unit-test green and still
fail to build or fail to boot — `tools/smoke.py` starts the app, waits, probes and
tears the process tree down, which is what `releasing` had mandated for months
with no mechanism behind it.

Detection is a data table (`MARKER_CHECKS`) covering Node, Deno, Python, Rust, Go,
Java, Kotlin, Ruby, PHP, Elixir, .NET and `make`; a new ecosystem is a row.
`.claude/project-checks.json` overrides any of it, `false` disables a kind as a
stated decision, and a configured tool that is not installed is **skipped and
named**, never failed.

---

## Gotchas

- **Set `PYTHONIOENCODING=utf-8` before running any tool script.** Several print
  `→` and `—`; the Windows console default (cp1252) raises `UnicodeEncodeError`
  and turns a passing run into a fake failure.
- **A hook bug's symptom is silence** — identical to "no problem". After editing
  any hook, fire it with `tools/run_hook.py` against a realistic payload.
- Hook scripts read input via `_hooklib.load_payload()`, so both stdin and
  `HOOK_PAYLOAD` work.
- **A skill is silently invisible** if it is a flat `.md` rather than
  `<name>/SKILL.md`, or if its frontmatter `name:` differs from its directory.
  Nothing errors — it just never appears. `tools/test_process_router.py` checks
  both.
- The `github` MCP server needs `GITHUB_TOKEN` in the environment. `gh` itself is
  already authenticated on this machine; if it ever needs redoing, `gh auth login`
  is an interactive browser flow that cannot be scripted, and the MSI installer
  needs admin rights — the working install is a user-local zip on `PATH`.

---

## Never

- Ignore a failing test, or weaken/delete one to make a build pass.
- Report a check as passing that was not actually run.
- Commit secrets or credentials.
- Push, merge, publish or deploy without explicit user approval.
- Create a duplicate implementation of something that already exists.
- Put AI attribution in git history. Two layers now: `attribution.commit`/`pr`
  are `""` in `~/.claude/settings.json` so the harness appends nothing, and
  `pre-commit/03-attribution-guard.py` DENIES a hand-written `-m` carrying a
  trailer — plus a `user.name`/`user.email` that resolves to an AI, which no
  per-message check would ever see. The "yours are unchecked" gap is closed.
