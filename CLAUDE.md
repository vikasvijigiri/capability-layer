# UAIOS — CLAUDE.md

A Claude Code capability layer: skills, lifecycle hooks and slash commands that
enforce a spec → plan → build → verify workflow, plus the knowledge docs that
carry state between sessions. There is no application code here.

This file is a bootloader. Keep it under ~150 lines and point at the thing that
owns the work rather than restating it. History belongs in `LOG.md` and git.

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
| `code-review` | 6 review | findings + a sign-off receipt |
| `delivering` | 7 deliver | merged / pushed / PR opened |
| `releasing` | 8 release | the change serving at a named target + a quoted smoke check |
| `knowledge-manager` | 9 record | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `decisions/` |
| `research` | — entered from any stage | `docs/research/YYYY-MM-DD-<topic>.md` |
| `systematic-debugging` | — entered on any failure | root cause + `ISSUES.md` entry |

### Subagents

Four, in `.claude/agents/<name>.md`. Each is dispatched by the skill that owns
the stage, only when the user has asked for subagents:

| Agent | Dispatched by | For | Parallel? |
|---|---|---|---|
| `source-digger` | `research` | one external source → a digest file | yes, 3-5 |
| `failure-investigator` | `systematic-debugging` | one independent failure → root cause | yes, one per failure |
| `diff-reviewer` | `code-review` | one review angle over one diff | yes, one per angle |
| `task-implementer` | `executing-plans` | one plan task | **no — never two at once** |

They exist to keep bulk out of the main context and to run independent work
concurrently. `tools/test_process_router.py` asserts each has a description
saying when *not* to use it, an explicit `tools:` allowlist (no line means it
inherits `Write`), a pinned model, and at least one skill that names it.

Every skill **must** also have a `## <name>` entry in
`.claude/routing/process-skills.md`; the skill listing is truncated against a
token budget, so that file is the only routing signal that always survives.
`tools/test_process_router.py` fails the build.

---

## Model and effort budget

Every skill declared `model: opus` + `effort: high` until 2026-08-02 — a default
nobody revisited, and `pre-run/05-process-skill-router.py` suggests a skill on
most turns, so it applied constantly. The policy now:

| Model | Skills | Why |
|---|---|---|
| `opus` | `brainstormer`, `writing-plans`, `research`, `systematic-debugging` | planning and diagnosis — open-ended, and a wrong answer is expensive |
| `sonnet` | `code-review`, `executing-plans`, `task-brief`, `verifying-work`, `delivering`, `releasing`, `knowledge-manager` | coding, checking, and fixed-shape procedure |
| `haiku` | agent `source-digger` | pure extraction, no judgement |

`effort` tracks the same axis: `high` for a judgement, `medium` for structured
work, `low` for a fixed-shape checklist. `systematic-debugging` keeps `opus`
though diagnosis is not planning — three 2026-08-02 bugs were caught in reasoning
alone and were invisible in the diff.

Two other levers: **`/fast`** (same Opus 5, less extended thinking — right for
doc sweeps and bulk edits, wrong for debugging), and **request shape**, which is
the biggest and is the user's. Deliberation goes on resolving ambiguity, not
solving problems; one goal per request cuts it directly.

Descriptions are injected **every turn** (~1,000 tokens for eleven) while
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

Raw equivalents, run from the repo root:

    python tools/test_hooks.py
    python tools/test_process_router.py
    python tools/test_hook_registration.py
    python tools/test_artifact_autocommit.py
    python tools/test_project_checks.py
    python tools/test_referenced_paths.py
    python tools/check_config_json.py
    python -m ruff check .
    python tools/run_checks.py --tier all --require-test   # both tiers
    python tools/smoke.py --url <url> --expect-status 200   # is it actually serving
    python tools/run_hook.py <event> '<json-payload>'   # fire one hook manually

Run `/verify` before declaring any work done.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | the eleven skills above, one directory each |
| `.claude/agents/` | four subagents; dispatched by skills for parallel work, one file each |
| `.claude/workflow.md` | stage → owning skill → artefact; the chain and its invariants |
| `.claude/routing/process-skills.md` | keyword → skill-name routing (mandatory per skill) |
| `.claude/hooks/<event>/` | nine hooks over seven events; `session-start`, `pre-run`, `post-run`, `pre-commit`, `pre-edit`, `pre-deploy`, `on-artifact-create` |
| `.claude/settings.json` | what actually fires; `hooks_registry.json` only documents intent |
| `.claude/commands/` | the four slash commands above |
| `tools/` | `run_checks.py` (one entry point for green), `smoke.py`, `run_hook.py`, six test suites, `check_config_json.py` |
| `docs/specs/`, `docs/plans/`, `docs/research/` | skill outputs, one dated file each |
| `docs/archive/` | the pre-2026-08-01 design layer; superseded, see `docs/archive/ARCHIVE.md` |
| `decisions/` | dated ADRs |
| `.claude/skills/releasing/references/` | platform packs — deploy/smoke/rollback per target |
| `.github/workflows/checks.yml` | CI; calls the same resolver, so it cannot drift from local |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

There is no global layer — `~/.claude/` holds no skills, agents or hooks.

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

**Review moves to the push/PR**, over the whole branch — a commit that needs a
human is not a checkpoint. `wip:` is deliberate: squash-merge collapses them.

Two things this depends on, both easy to break:

- `UAIOS_AUTOCOMMIT_RUNNING` guards re-entry. `tools/test_hooks.py` fires the
  whole `post-run` event, so without it the hook runs the suites which run the
  hook, unbounded — presenting as a hang, not an error.
- Its commits **bypass `PreToolUse`**, so the secret and attribution checks run
  *inline* from `_hooklib`; `pre-commit/01-secret-scan.py` never sees them.

Nineteen hooks were deleted on 2026-08-02, including every process-compliance
gate and the staging guards. Why, and the deadlock that proved it: `LOG.md`
2026-08-02 19:26 / 21:30, and `docs/2026-08-02-git-flow-walkthrough.md`.

## Two check tiers

Cost differs by an order of magnitude, and a gate nobody can afford to run is a
gate that gets switched off. `.claude/hooks/_projectchecks.py` owns both; every
caller goes through `tools/run_checks.py` so local, the hook and CI cannot
disagree about what green means.

| Tier | Kinds | Runs | Gates |
|---|---|---|---|
| fast | lint · typecheck · test | end of every turn, seconds | the auto-commit |
| slow | build · audit · e2e · smoke | once before delivery, minutes | push / PR, and CI on pull requests |

    python tools/run_checks.py --tier all --require-test

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
