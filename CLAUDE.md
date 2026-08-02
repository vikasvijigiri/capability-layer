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
`session-start/01-env-check.py` reports any skill that lacks one, and
`tools/test_process_router.py` fails the build.

---

## Commands

    /verify         all six test suites + env check + hook registration + frontmatter parse
    /save           stage, describe and commit (local only)
    /wip            branch, uncommitted work, which knowledge docs went stale
    /skills-doctor  skill layer health — description budget, YAML, name mismatches

Raw equivalents, run from the repo root:

    python tools/test_hooks.py
    python tools/test_process_router.py
    python tools/test_hook_registration.py
    python tools/test_docs_staleness.py
    python tools/test_artifact_autocommit.py
    python tools/test_index_scope_guard.py
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
| `.claude/hooks/<event>/` | lifecycle hooks; `session-start`, `pre-run`, `post-run`, `pre-commit`, `pre-edit`, `pre-deploy`, `on-*` |
| `.claude/settings.json` | what actually fires; `hooks_registry.json` only documents intent |
| `.claude/commands/` | the four slash commands above |
| `tools/` | `run_hook.py` + six test suites |
| `docs/specs/`, `docs/plans/`, `docs/research/` | skill outputs, one dated file each |
| `docs/archive/` | the pre-2026-08-01 design layer; superseded, see `docs/archive/ARCHIVE.md` |
| `decisions/` | dated ADRs |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

There is no global layer — `~/.claude/` holds no skills, agents or hooks.

---

## Knowledge docs

Six files at the repo root carry state between sessions. Hooks read and gate on
them, so they are code, not commentary:

`TASK.md` (active task) · `PLAN.md` · `HANDOFF.md` (current work, pending, next)
· `LOG.md` (history) · `ISSUES.md` · `MEMORY.md`

Two hooks watch them now: `pre-run/04-docs-staleness.py` warns when they drift
from the diff, and `post-run/06-artifact-autocommit.py` commits them along with
everything else the turn changed — the only hook here that acts rather than asks.

## The commit loop

Commits are automatic and local. `post-run/06-artifact-autocommit.py` fires at
the end of every turn and commits what changed, as a `wip:` checkpoint, if and
only if all five hold:

| Gate | Refuses when |
|---|---|
| branch | on `main`/`master`/`develop`/`release` |
| size | more than `MAX_FILES = 25` changed — that is a unit of work, not a checkpoint |
| secrets | any changed file matches `_hooklib.SECRET_PATTERNS` |
| suites | any `tools/test_*.py` exits non-zero |
| message | the generated subject matches `_hooklib.AI_ATTRIBUTION_PATTERNS` |

Every clause is a fact about the artefact, never about process. A refusal is
always spoken; nothing is skipped silently. It **never pushes** and never
`git add .` — always an explicit pathspec.

**Review moves to the push/PR**, over the whole branch, because a commit that
needs a human is not a checkpoint. The `wip:` prefix is deliberate: squash-merge
collapses them into the one message a human writes.

Two things this depends on, both easy to break:

- `UAIOS_AUTOCOMMIT_RUNNING` guards re-entry. `tools/test_hooks.py` fires the
  whole `post-run` event, so without it the hook runs the suites which run the
  hook, unbounded — it presents as a hang, not an error.
- The hook's commits **bypass `PreToolUse` entirely**, so the secret scan and the
  attribution check are enforced *inline* from `_hooklib`, not by
  `pre-commit/01-secret-scan.py`, which never sees them.

`post-run/05-docs-gate.py` and `pre-commit/05-docs-required.py` were deleted on
2026-08-02, along with `pre-commit/03-review-gate.py`. All three gated *process
compliance* rather than artefact correctness, and the review gate fingerprinted
the whole working tree — so writing the log entry `05-docs-required` demanded
invalidated the receipt `03-review-gate` demanded, a deadlock proven by
measurement. Five comparable repos were read and not one enforces process this
way; see `LOG.md` 2026-08-02 19:26 and `docs/2026-08-02-git-flow-walkthrough.md`.

Staging is guarded by `session-start/03-index-baseline.py` plus
`pre-commit/06-index-scope-guard.py`: the first records what was already staged
when the session began, the second asks before a blanket `git add` or before a
commit spends files this session never staged. `ALLOW_WIDE_STAGE=1` skips it.

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
- Put AI attribution in git history — `pre-commit/04-delivery-guard.py` denies
  the commit.
