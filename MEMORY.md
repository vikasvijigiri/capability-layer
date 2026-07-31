# Project Memory

<!-- Engineering-relevant facts and context worth persisting across sessions for
this repo. Distinct from Claude Code's own auto-memory index under
~/.claude/projects/<slug>/memory/ -- this file is checked into the repo. -->

## Skills and capabilities

- There is **no global layer**. `~/.claude/` holds no skills, agents, hooks or workflows;
  everything lives in this repo. A backup of the removed global config is at
  `~/.claude/backups/global-config-20260730-221402/`.
- All 61 skills are at `.claude/skills/<name>/SKILL.md`. Claude Code only discovers that
  exact layout — a flat `.md` file, or a frontmatter `name:` that differs from the
  directory name, is silently invisible. `skills.json` records `discoverable` per skill
  for exactly this reason.
- Capability skills are prefixed `<domain>-`; the 15 unprefixed ones are cross-cutting
  process skills. `deployment-pilot` is a process skill despite matching a domain prefix,
  so prefix-matching alone mis-files it — `generate_registry.py` excludes it explicitly.
- Every artefact type is top-level under `.claude/` with the same `<domain>-` prefix:
  `blueprints/`, `workflows/`, `validators/`, `playbooks/`, `templates/`.
  `.claude/capabilities/<domain>/` keeps only `index.md` — the `Keywords:` line the
  router scans, plus the precedence rules a flat list cannot express.
- Copies under `capabilities/<domain>/` carry a **Superseded** banner. They are history:
  never edit or link to them. The registries exclude them on purpose — two routable paths
  for one artefact means the stale one eventually wins.
- Prefixing traps that already bit once, both handled explicitly in the generator:
  a stem already starting with its domain (`ai-output-validator`) must not become
  `ai-ai-output`, and `deployment-pilot` is a *process* skill that matches a domain
  prefix, so prefix-matching alone mis-files it.
- Registries are **generated**. Run `python tools/generate_registry.py`; never hand-edit
  `.claude/registry/*.json`. Any diff after regenerating is real drift.

## Skill and agent descriptions

- The description is the **only** trigger surface. Every skill and agent follows the
  `task-intake` shape: what it does → quoted real-user phrasings → `Prefer this over …`
  → `Do NOT use for …`. All 73 conform; keep new ones to it.
- Include **vague, symptom-level** phrasings, not just expert terms. `"429 handling"` only
  fires for someone who already knows the answer; `"someone is hammering the api"` is how
  the problem actually arrives. Aim for ~7 quoted phrases spanning both registers.
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
  Descriptions currently average ~620, so there is headroom, but a long one loses its tail.
- Twelve skills also carry `provides`, `requires`, `produces_artifact` and `retryable`.
  These are **not** harness fields and Claude Code ignores them — do not "clean them up".
  `build-mvp.js`'s `CAPABILITY_MANIFEST` mirrors `provides`/`requires` by hand to route
  its phases, and as of 2026-07-31 the two agree exactly: every capability named in the
  manifest is declared by some skill, and the only declared capability absent from it is
  `autonomous-build` (mvp-builder's own, which it correctly never dispatches to itself).
  Adding one of these keys to a thirteenth skill does nothing unless the manifest is
  updated too.
- **Agents use a different schema from skills**: `name`, `description`, `tools` (not
  `allowed-tools`), and `model`. All 12 lacked `model` until 2026-07-31 and therefore
  silently inherited the parent's, bypassing the per-phase model rule entirely. Agent
  descriptions cost ~1.9k tokens per session on top of the skills' ~13.5k.

## Workflows

- **There is no workflow runtime in Claude Code.** The files in `.claude/workflows/` are
  documents to follow, not executables. Nothing discovers or fires them.
- `build-mvp.js` is a phase *specification*, not a script: it calls host-injected
  `agent()`/`phase()` primitives and has a top-level `return`, so Node rejects it with
  `SyntaxError: Illegal return statement`. `mvp-builder` reads it for phase order and
  drives each phase with the real Skill and Agent tools.
- Workflows, blueprints and validators are reached through the **`## Routing` section in
  each capability skill's body** - not through discovery. The body costs no context until
  the skill loads, which is why the routing lives there and not in the description.
- Every capability skill names a required validator. CLAUDE.md makes running it mandatory
  before a side effect; a skipped validator is a failed run.

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
