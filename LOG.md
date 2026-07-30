# Log

<!-- Append new entries at the TOP, never rewrite old ones.
Format: ## YYYY-MM-DD HH:MM -->

## 2026-07-31 02:20
Added `brainstormer` (83 skills). Runs on `model: opus` and enters plan mode from its body,
since frontmatter has no plan-mode field - `disallowed-tools: Edit, Write, NotebookEdit` is
the backstop if plan mode is not entered.

## 2026-07-31 02:00
Populated the empty pipeline stages with 21 new skills: Analyze (impact-analysis,
root-cause-analysis, feasibility-check), Plan (execution-planner, work-decomposition),
both human gates (approval-brief, change-summary), plus safe-refactor, dependency-upgrade,
acceptance-verifier, simplify, requirements-traceability, release-packager, runbook-writer,
blueprint-promoter, retrospective and five domain skills. 82 skills total. Fixed
generate_registry.py, which had hardcoded the 15 process skills and so filed the new ones
under invented capabilities ("impact", "approval", "root"); membership is now derived from
whether the prefix names a real capability directory.

## 2026-07-31 01:10
Fixed stale cross-references inside 20 of 25 migrated artefacts - the earlier rename pass
only covered capability `index.md` files, so blueprints, workflows, validators, the playbook
and the template still named pre-migration artefacts (`oauth-skill`, `oauth-validator`).
Also corrected each validator's `on-validate-fail` payload, which reported a `validator`
name matching no file. All artefact references now resolve.

## 2026-07-31 00:45
Connected the capability layer to its artefacts: added a `## Routing` section to all 46
capability skills naming the required validator, the blueprint that takes precedence, and
the workflow for the multi-step case. Previously no skill referenced any of them, so the
mandatory-validator rule in CLAUDE.md had no path to fire. Fixed `mvp-builder` step 4,
which invoked a `Workflow` tool that does not exist; `build-mvp.js` is unrunnable
(host-injected primitives, top-level return) and is now banner-marked as a specification.

## 2026-07-31 00:15
Rewrote all 73 skill/agent descriptions to the `task-intake` shape (what it does -> quoted
user phrasings -> Prefer -> Do NOT). Added vague symptom-level phrasings alongside expert
terms; 545 quoted trigger phrases total, avg 7.5 each. Found and fixed a YAML break in
`design-system` (`: "` parses as a mapping, silently blanking the description) and the same
latent hazard in `security-reviewer`. Retitled all 25 migrated artefacts, whose H1s still
named their pre-migration capability paths.

## 2026-07-30 23:40
Migrated the remaining 25 capability artefacts to top-level `.claude/{blueprints,
workflows,validators,playbooks,templates}/` with `<domain>-` prefixes. Originals retained
under `capabilities/` with a Superseded banner and deliberately excluded from the
registries. Capability routing sections rewritten to canonical paths and post-migration
skill names. Added `artefacts.json` (26 entries); registries now number five.

## 2026-07-30 23:05
Migrated all 46 capability skills to `.claude/skills/<domain>-<name>/SKILL.md`, making
every skill discoverable by the Skill tool. Domain prefix disambiguates same-named
responsibilities across capabilities (`backend-caching-strategy` vs `ai-*`). Added
cross-capability "use X instead" pointers to 46 descriptions. `capabilities/` now keeps
only index/blueprints/workflows/validators. 61 skills total; `skills.json` registry added.

## 2026-07-30 22:20
Removed the global `~/.claude` layer (15 skills, 12 agents, 8 hooks, 1 workflow, MCPS.md,
settings hooks block); backed up to `~/.claude/backups/global-config-20260730-221402/`.
Promoted all of it into this repo: agents with frontmatter, skills under `.claude/skills/`,
hooks mapped onto existing domain events plus new `pre-edit` and `pre-deploy`.

## 2026-07-30 21:50
Added `pre-run/02-capability-router.py` — mechanical keyword scan injecting capability
matches on every prompt, replacing a protocol that relied on recall and measurably never
fired. `generate_registry.py` now generates all registries; `mcps.json` had listed 1 of 27.

## 2026-07-30 21:20
Added `pre-commit/02-branch-guard.py` (denies commits onto main/master/develop/release)
and `post-run/03-checkpoint.py` (per-turn snapshot under `refs/checkpoints/`, local
only). Added `/save` command for explicit, non-pushing commits.

## 2026-07-30 21:05
`git init` run on this repo. This unblocked the global `bootstrap_repo` SessionStart
hook, which had been silently returning on `find_git_root() is None` — it then scaffolded
TASK/PLAN/MEMORY/HANDOFF/LOG/ISSUES and `decisions/README.md`.

## 2026-07-30 20:55
Dropped the `tools/cc_hook_adapter.py` bridge and registered all hook scripts directly in
`.claude/settings.json`, matching the global `~/.claude/hooks` pattern. Routing logic
moved into each script as a self-filter. See `decisions/2026-07-30-direct-hook-registration.md`.

## 2026-07-30 20:30
Wired `.claude/hooks/` into Claude Code lifecycle events for the first time. Measured
that `PostToolUse` is never emitted for a failed tool call; failures arrive on
`PostToolUseFailure` instead, which now drives `on-error`/`on-validate-fail`/`on-deploy-failure`.

## 2026-07-30 19:15
Repaired MCP configuration: `fetch`, `time` and `git` were all broken by `mcp` SDK 2.0.0
(renamed `McpError`, removed `Server.list_tools`); pinned `mcp==1.29.0`. Added `figma`,
`sentry`, `notion`, `linear`.
