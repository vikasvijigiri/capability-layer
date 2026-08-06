# Capability Layer

This repository contains a harness-neutral, production-oriented agent
capability layer for software delivery. It provides skills, agents, commands,
workflows, hooks, safety checks, and durable project documentation for Claude
Code, Codex, Gemini, and VS Code agent hosts.

## Setup

Open the repository in the chosen agent host. Read [`AGENTS.md`](AGENTS.md),
[`CLAUDE.md`](CLAUDE.md), and [`harnesses.json`](harnesses.json). Install the
Node dependencies when using the optional repository runner:

```text
npm install
```

## Verification

Run the complete local contract suite:

```text
python tools/run_checks.py --tier all --require-test
```

## Architecture

- `.claude/` — canonical skills, agents, commands, workflows, hooks, rules,
  settings, and project checks.
- `AGENTS.md` — harness-neutral operating contract.
- `harnesses.json` — canonical path and host execution manifest.
- `docs/` — baselines, pilots, plans, research, and specifications.
- `tools/` — deterministic validators, runners, and test suites.
- `templates/` and `guide/` — authoring standards for the capability layer.

The normal execution model is host-managed: the IDE agent supplies the model
session, while the repository supplies the workflow contract and evidence
gates. The standalone SDK runner is optional.

## Durable project documents

[`knowledge-manager`](.claude/skills/knowledge-manager/SKILL.md) owns
`README.md`, `TASK.md`, `HANDOFF.md`, `MEMORY.md`, `LOG.md`, `ISSUES.md`, and
`decisions/`. [`capability-layer-maintenance`](.claude/skills/capability-layer-maintenance/SKILL.md)
owns the capability-layer contracts and wiring.

## Related docs

- [Workflow policy](.claude/workflow.md)
- [Universal agent contract](AGENTS.md)
- [Harness manifest](harnesses.json)
- [Project handoff](HANDOFF.md)
