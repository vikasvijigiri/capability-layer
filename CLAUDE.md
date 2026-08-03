# UAIOS — CLAUDE.md

A Claude Code capability layer: skills, lifecycle hooks and slash commands that
enforce a spec → plan → build → verify workflow, plus the knowledge docs that
carry state between sessions. There is no application code here.

This file is a bootloader: point at the thing that owns the work rather than
restating it. History belongs in `LOG.md` and git.

**Max 300 lines, and `tools/test_referenced_paths.py` enforces it** by reading
that number from this sentence. It said 150 for two weeks while the file grew to
282 — an unchecked limit is a wish. 300 is set just above the current size on
purpose: growth now has to be paid for by cutting something, and the suite says
so rather than a reviewer noticing.

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

| Skill | Stage | Produces |
|---|---|---|
| `task-brief` | 1 frame | `TASK.md` — six fields, approved |
| `brainstormer` | 2 design | `docs/specs/YYYY-MM-DD-<topic>-design.md` |
| `writing-plans` | 3 plan | `docs/plans/YYYY-MM-DD-<feature>.md` |
| `executing-plans` | 4 execute | the thing itself; ticked plan checkboxes |
| `verifying-work` | 5 validate | coverage verdict + the unbacked set |
| `no-slop` | 6 sweep | repo-wide slop findings + approved repairs |
| `code-review` | 7 review | findings + a sign-off receipt |
| `delivering` | 8 deliver | merged / pushed / PR opened |
| `releasing` | 9 release | the change serving at a named target + a quoted smoke check |
| `knowledge-manager` | 10 record | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `decisions/` |
| `research` | — entered from any stage | `docs/research/YYYY-MM-DD-<topic>.md` |
| `systematic-debugging` | — entered on any failure | root cause + `ISSUES.md` entry |
| `skill-authoring` | — entered to change this layer | a wired skill + a green `new_skill_check.py` |

`pre-run/05-process-skill-router.py` falls back to **prompt shape** when no
keyword matches: an imperative, or a framing plus a verb, names `task-brief`.
"Build an AI platform that assists scientists" matched nothing and the chain
never started. A question about existing state is left alone. The corpus in
`tools/test_process_router.py` is real prompts, not invented ones.

**The fallback is not a safety net for missing keywords.** `TASK_VERBS` holds
only verbs that ask for a *change*; `check`, `audit`, `review` and `verify` are
deliberately absent, because an audit routed to `task-brief` is routed to the
wrong stage. "Check if the .claude folder is clean" therefore matched nothing at
all until 2026-08-03 — the repair belongs in the owning skill's `Keywords:`
line, never in `TASK_VERBS`.

### Subagents

Four, in `.claude/agents/<name>.md`. Each is dispatched by the skill that owns
the stage, only when the user has asked for subagents:

`source-digger` (research), `failure-investigator` (debugging),
`diff-reviewer` (review) fan out; `task-implementer` **never runs two at once**.
`.claude/workflow.md` carries the table. `tools/test_process_router.py` asserts
each has a "do NOT use" clause, a `tools:` allowlist, a pinned model, and a
dispatcher that names it — and that it names its dispatcher back.

Every skill **must** also have a `## <name>` entry in
`.claude/routing/process-skills.md`; the skill listing is truncated against a
token budget, so that file is the only routing signal that always survives.
`tools/test_process_router.py` fails the build.

---

## Model and effort budget

Every skill declared `model: opus` + `effort: high` until 2026-08-02 — a default
nobody revisited, and `pre-run/05-process-skill-router.py` suggests a skill on
most turns, so it applied constantly. The policy now:

`opus` for planning and diagnosis, `sonnet` for coding and procedure, `haiku`
for pure extraction — the per-skill values are in each `SKILL.md` frontmatter,
which is the source of truth. `effort` tracks the same axis.
`systematic-debugging` keeps `opus` though diagnosis is not planning: three
2026-08-02 bugs were caught in reasoning alone and were invisible in the diff.

Two other levers: **`/fast`** (same Opus 5, less extended thinking — right for
doc sweeps and bulk edits, wrong for debugging), and **request shape**, which is
the biggest and is the user's. Deliberation goes on resolving ambiguity, not
solving problems; one goal per request cuts it directly.

Descriptions are injected **every turn** (~1,100 tokens for thirteen) while
`.claude/routing/process-skills.md` is read by a hook and costs nothing — so
trigger breadth belongs in the routing file and descriptions stay ~380 chars.
`session-start/02-bootstrap-docs.py` is budgeted for the same reason: it injected
26,990 chars before anyone typed, and now clips to ~5,500.

---

## Commands

    /verify         the project's own lint + test commands, hook imports, frontmatter parse
    /save           stage, describe and commit (local only)
    /wip            branch, uncommitted work, which knowledge docs went stale
    /skills-doctor  skill layer health — description budget, YAML, name mismatches
    /git-state      exact counts: committed, staged, unstaged, untracked, branch scope
    /install-layer  copy this layer into another repo — wraps `.claude/install.py`

Raw equivalents, run from the repo root:

    python tools/test_hooks.py
    python tools/test_process_router.py
    python tools/test_hook_registration.py
    python tools/test_artifact_autocommit.py
    python tools/test_no_slop.py
    python tools/test_referenced_paths.py
    python tools/test_project_checks.py
    python tools/check_config_json.py
    python -m ruff check .
    python tools/new_skill_check.py <name>|--all   # is one skill actually reachable
    python tools/run_checks.py --tier all --require-test   # both tiers
    python tools/smoke.py --url <url> --expect-status 200   # is it actually serving
    python tools/run_hook.py <event> '<json-payload>'   # fire one hook manually

Run `/verify` before declaring any work done.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | the thirteen skills above, one directory each |
| `.claude/agents/` | four subagents; dispatched by skills for parallel work, one file each |
| `.claude/workflow.md` | stage → owning skill → artefact; the chain and its invariants |
| `.claude/routing/process-skills.md` | keyword → skill-name routing (mandatory per skill) |
| `.claude/hooks/<event>/` | eleven hooks over eight events; `session-start`, `pre-run`, `post-run`, `pre-commit`, `pre-edit`, `pre-deploy`, `on-artifact-create`, `on-repo-create` |
| `.claude/settings.json` | what actually fires; `hooks_registry.json` only documents intent |
| `.claude/commands/` | the six slash commands above |
| `.claude/install.py` | ports the layer into another repo; `/install-layer` wraps it |
| `tools/` | `run_checks.py` (one entry point for green), `smoke.py`, `run_hook.py`, the test suites, `check_config_json.py` |
| `docs/specs/`, `docs/plans/`, `docs/research/` | skill outputs, one dated file each |
| `docs/archive/` | the pre-2026-08-01 design layer; superseded, see `docs/archive/ARCHIVE.md` |
| `decisions/` | dated ADRs |
| `.claude/skills/releasing/references/` | platform packs — deploy/smoke/rollback per target |
| `.github/workflows/checks.yml` | CI; calls the same resolver, so it cannot drift from local |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

There is no global layer — `~/.claude/` holds no skills, agents or hooks.

**`../physrun/` is a sibling repo, not part of this one** — the first product
built with this layer, and the first test of whether the layer ports. It carries
the whole layer as of 2026-08-03, plus its own `CLAUDE.md` and docs. Copying this
file wholesale would be wrong; it asserts "there is no application code here"
and a hook count, both false there. Porting found three bugs in a day, none of
them findable from inside this repo. See `LOG.md` 2026-08-03 14:30.

---

## Knowledge docs

Six files at the repo root carry state between sessions. Hooks read and gate on
them, so they are code, not commentary:

`TASK.md` (active task) · `PLAN.md` · `HANDOFF.md` (current work, pending, next)
· `LOG.md` (history) · `ISSUES.md` · `MEMORY.md`

**Nothing watches them any more.** `post-run/06-artifact-autocommit.py` commits
them along with everything else the turn changed, but it never checks whether
they were written — so a turn can be checkpointed with no log entry behind it.
The staleness warner, the Stop gate and the commit gate were all deleted on
2026-08-02. Invoking `knowledge-manager` is now a habit, not a prompted one.

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

Three attempts at the same failure and it stops suggesting and escalates, because
a fix that has not converged in three passes is not converging. Green clears the
state and closes the loop **forward**: it names `verifying-work` → `code-review`
→ `delivering`, so "no longer failing" is not mistaken for "finished".

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
- Put AI attribution in git history. `04-delivery-guard.py` denied this and was
  deleted on 2026-08-02; now only `_hooklib.AI_ATTRIBUTION_PATTERNS` checks it,
  and only over messages the auto-commit generates. Yours are unchecked.
