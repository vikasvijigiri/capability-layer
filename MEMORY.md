# Project Memory

<!-- Durable engineering facts for this repository. Current handoff state belongs
in HANDOFF.md; chronological events belong in LOG.md. -->

## Canonical layer

- `.claude/` is the only repository-native capability source.
- `AGENTS.md` is the harness-neutral operating contract.
- `harnesses.json` is the cross-harness path and execution manifest.
- Claude Code consumes `.claude/` natively; other hosts must consume or project
  those same files without creating a parallel source.
- `capability-layer-maintenance` owns capability-layer contracts, wiring,
  skills, agents, commands, hooks, rules, settings, and validators.
- `knowledge-manager` owns `README.md`, `TASK.md`, `HANDOFF.md`, `MEMORY.md`,
  `LOG.md`, `ISSUES.md`, and `decisions/`.

## Skills and routing

- Skills live at `.claude/skills/<name>/SKILL.md`; directory and frontmatter
  names must match exactly.
- Skill descriptions are the trigger surface. They must include real trigger
  phrasings and a `Do NOT use` boundary.
- The current layer has 14 skills and 11 agents. Product stages are defined by
  `.claude/workflow.md`; capability maintenance is off-chain.
- There is no `routing/process-skills.md` keyword router. Do not recreate one.

## Hooks

- Hooks are registered in `.claude/settings.json` and documented in
  `.claude/hooks/hooks_registry.json`.
- Hooks may detect drift, enforce safety, or record mechanical state.
- Hooks must not author strategic content such as README, CLAUDE.md, AGENTS.md,
  TASK.md, HANDOFF.md, MEMORY.md, LOG.md, ISSUES.md, harnesses.json, workflow
  policy, or decisions.
- `session-start/02-bootstrap-docs.py` reports missing scaffolding without
  creating documents.
- `post-run/07-layer-drift.py` performs read-only path and harness checks.
- `post-run/03-checkpoint.py` and the auto-commit hook write only recovery or
  Git state through their documented mechanisms.

## Verification

- Run `python tools/run_checks.py --tier all --require-test` before claiming
  completion.
- The suite includes skill routing, hook registration, hook policy, workflow,
  agents, commands, referenced paths, harness contracts, SDK runner tests, and
  dependency audit.
- A dry-run or host handoff is not evidence of a live product implementation;
  live IDE-hosted execution must be reported separately.

## MCP and local configuration

- `.mcp.json` and `.vscode/mcp.json` use different schemas and must remain
  synchronized deliberately.
- `.claude/settings.local.json` and other machine-local state must remain
  ignored and must not become part of the shared contract.
