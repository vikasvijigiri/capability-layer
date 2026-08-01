# Project Memory

<!-- Engineering-relevant facts and context worth persisting across sessions for
this repo. Distinct from Claude Code's own auto-memory index under
~/.claude/projects/<slug>/memory/ -- this file is checked into the repo. -->

## Skills

The capability layer (85 skills, 12 agents, blueprints, workflows, validators, templates,
playbooks, MCP docs, generated registries, nine-domain capability routing) was deleted on
2026-08-01. Everything is recoverable from commit `eaab430`. Two skills remain,
`brainstormer` and `writing-plans`, both adopted from `obra/superpowers`. The facts below
outlived the teardown; anything tied to the deleted machinery went with it.

- There is **no global layer**. `~/.claude/` holds no skills, agents, hooks or workflows;
  everything lives in this repo. A backup of the removed global config is at
  `~/.claude/backups/global-config-20260730-221402/`.
- Skills live at `.claude/skills/<name>/SKILL.md`. Claude Code only discovers that exact
  layout — a flat `.md` file, or a frontmatter `name:` that differs from the directory
  name, is silently invisible.
- **The skill listing is truncated against a token budget**, and which descriptions render
  varies between turns, so a skill can be untriggerable on the turn that needed it. This is
  why `routing/process-skills.md` is load-bearing rather than redundant, and why the budget
  is a design constraint on what gets added back, not a cleanup task for later.
- The description is a skill's only *listing-side* trigger surface. Shape that works:
  what it does → quoted real-user phrasings → `Prefer this over …` → `Do NOT use for …`.
  Include **vague, symptom-level** phrasings, not just expert terms — `"429 handling"` only
  fires for someone who already knows the answer; `"someone is hammering the api"` is how
  the problem actually arrives.
- **Never write `: "` inside a description.** An unquoted YAML scalar containing
  colon-space-quote parses as a mapping and the description silently vanishes — the skill
  stays listed but becomes untriggerable. Use ` - "` instead. (Bare `: ` mid-sentence
  survives Claude Code's parser but fails strict YAML; avoid it too.)
- Beware `.md` inside a description when editing programmatically — a regex that splits on
  `.` will slice `DESIGN.md` in half. Two descriptions were corrupted this way.
- Skill frontmatter supports exactly these fields: `name`, `description`, `when_to_use`,
  `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`,
  `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`,
  `background`, `hooks`, `paths`, `shell`. **There is no plan-mode or permission-mode
  field** - a skill that should run in plan mode must call `EnterPlanMode` from its body,
  and use `disallowed-tools` as the backstop.
- `description` + `when_to_use` are truncated at **1,536 characters** in the skill listing.
- `user-invocable:` is **not** what makes a skill slash-invocable. Skills without it work
  as `/name` anyway.
- **Agents use a different schema from skills**: `name`, `description`, `tools` (not
  `allowed-tools`), and `model`. An agent without `model` silently inherits the parent's.
- **There is no workflow runtime in Claude Code.** Files under a `workflows/` directory are
  documents to follow, not executables. Nothing discovers or fires them.

## Recurring bug class

**Prose declares a capability the wiring does not implement.** Five instances before the
teardown: a skill whose `allowed-tools` omitted `Skill` and so could never invoke the
skills its own body named; a hook registered on an event that never fires; six skills
documented as read-only while holding unrestricted tools; a staleness hook asking the wrong
question. None were catchable by the hook suite, which invokes scripts directly and
therefore tests the script and never the registration. Check the wiring, not the prose.

## Hooks

- Hook scripts under `.claude/hooks/<event>/` have **two** callers and must work for
  both: Claude Code (payload on stdin, registered in `.claude/settings.json`) and
  validators (payload in `HOOK_PAYLOAD`, via `tools/run_hook.py`). Use
  `_hooklib.load_payload()`, which handles both.
- `load_payload()` checks `HOOK_PAYLOAD` **before** stdin, and that order must not be
  "tidied". `run_hook.py` does not redirect the child's stdin, so a hook that reads
  stdin first blocks forever on an inherited pipe. See `ISSUES.md` 2026-07-30.
- `PostToolUse` fires **only on success** and its payload carries no exit code. Tool
  failures arrive on `PostToolUseFailure`, whose failure reason is in `error` — not
  `error_message`, despite what the published docs say. It also carries `is_interrupt`,
  which distinguishes a user cancellation from a real failure.
- Scripts registered on a broad event must self-filter (check the command, the branch,
  the tool name). There is no router; that is deliberate.
- Hook changes in `.claude/settings.json` take effect immediately. No restart needed.

## MCP

- The `uvx`-based servers (`fetch`, `time`, `git`) pin `mcp==1.29.0` via `--with`. They
  float their dependency and SDK 2.x breaks them (`McpError` renamed, `Server.list_tools`
  removed). Do not drop the pin without re-testing all three.
- `.mcp.json` (Claude Code) and `.vscode/mcp.json` (VS Code) are kept in sync by hand and
  use different schemas. Change both.
- Project MCP servers only load when the working directory is this repo. Running Claude
  from a parent or sibling folder silently shows only user-scope servers.

## Git

- `refs/checkpoints/*` are machine-written turn snapshots from `post-run/03-checkpoint.py`.
  They are not branches, are never pushed, and are pruned to the newest 50. Safe to delete.
- Commits to `main`/`master`/`develop`/`release` are denied by `pre-commit/02-branch-guard.py`.
  Override a single command with `ALLOW_MAIN_COMMIT=1`; the initial commit is exempt.
