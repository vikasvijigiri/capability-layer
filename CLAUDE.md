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

- `task-brief` — rough ask → six-field brief (Goal / Constraints / Inputs /
  Outputs / Done-check / Out-of-scope), approved, written to `TASK.md`.
- `brainstormer` — open question → design spec at
  `docs/specs/YYYY-MM-DD-<topic>-design.md`.
- `writing-plans` — approved spec → task-by-task plan at
  `docs/plans/YYYY-MM-DD-<feature>.md`.

Every skill **must** also have a `## <name>` entry in
`.claude/routing/process-skills.md`; the skill listing is truncated against a
token budget, so that file is the only routing signal that always survives.
`session-start/01-env-check.py` reports any skill that lacks one, and
`tools/test_process_router.py` fails the build.

---

## Commands

    /verify         all four test suites + env check + hook registration + frontmatter parse
    /save           stage, describe and commit (local only)
    /wip            branch, uncommitted work, which knowledge docs went stale
    /skills-doctor  skill layer health — description budget, YAML, name mismatches

Raw equivalents, run from the repo root:

    python tools/test_hooks.py
    python tools/test_process_router.py
    python tools/test_docs_gates.py
    python tools/test_docs_staleness.py
    python tools/run_hook.py <event> '<json-payload>'   # fire one hook manually

Run `/verify` before declaring any work done.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | `task-brief`, `brainstormer`, `writing-plans` |
| `.claude/routing/process-skills.md` | keyword → skill-name routing (mandatory per skill) |
| `.claude/hooks/<event>/` | lifecycle hooks; `session-start`, `pre-run`, `post-run`, `pre-commit`, `pre-edit`, `pre-deploy`, `on-*` |
| `.claude/settings.json` | what actually fires; `hooks_registry.json` only documents intent |
| `.claude/commands/` | the four slash commands above |
| `tools/` | `run_hook.py` + four test suites |
| `docs/specs/`, `docs/plans/` | skill outputs |
| `docs/00-*.md … 17-*.md` | design notes for the *pre-2026-08-01* layer — stale, read with suspicion |
| `decisions/` | dated ADRs |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

There is no global layer — `~/.claude/` holds no skills, agents or hooks.

---

## Knowledge docs

Six files at the repo root carry state between sessions. Hooks read and gate on
them, so they are code, not commentary:

`TASK.md` (active task) · `PLAN.md` · `HANDOFF.md` (current work, pending, next)
· `LOG.md` (history) · `ISSUES.md` · `MEMORY.md`

Three hooks watch them at three moments: `pre-run/04-docs-staleness.py` warns
when they drift from the diff, `post-run/05-docs-gate.py` tries to block the
turn from ending (`Stop` blocking is unproven in this build), and
`pre-commit/05-docs-required.py` denies a multi-file commit that touches neither
`LOG.md` nor `HANDOFF.md` — `PreToolUse` deny is the mechanism that demonstrably
works. Override with `ALLOW_UNLOGGED_COMMIT=1` when a commit genuinely warrants
no log entry.

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
