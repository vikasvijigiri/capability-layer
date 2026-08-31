# `.claude/` — what is in here and what fires

The capability layer: skills, subagents, lifecycle hooks, slash commands and the
policy they enforce. This file orients a contributor or an agent arriving cold.
It is a map, not a contract — every directory below owns its own rules, and where
this file and one of them disagree, the directory is right.

**Start with `workflow.md`.** It owns the nine-stage lifecycle, the two human
gates, the entry rules and the safety rails. Nothing here restates it.

## What actually runs

`settings.json` is the only thing the host reads. `hooks/hooks_registry.json`
documents the contract and cannot enforce it — when the two disagree, the
registry is the one that is wrong.

| Event | Fires |
|---|---|
| `SessionStart` | `session-init/02-session-context.py`, `03-state-report.py` |
| `UserPromptSubmit` | `prompt-intake/01-entry-classifier.py` |
| `PreToolUse` | `pre-tool/01-halt-guard.py`, then the commit, deploy and edit guards by matcher |
| `PostToolUse` | `post-edit-validation/02-hook-self-test-nudge.py`, `context-budget/01-context-cost.py` |
| `Stop` | `stop-finalization/00-dispatch.py`, which runs checkpoint, auto-commit, layer-drift and chain-continuity in one process |

A hook is silent when it works and silent when it is broken, which is the trap
this layer has fallen into most often. **Fire one by hand after editing it:**

    python tools/run_hook.py <event> '<json payload>'

Every hook declares one of four behaviours in its module docstring, and a suite
checks that it does: detect drift · enforce safety · record state · never author
strategic content. A hook may report that a document needs updating; it may not
write the document.

## The directories

| | |
|---|---|
| `skills/` | 15 capabilities, triggered **only** by their own `description:` frontmatter. `<skill>/references/` holds depth loaded per task, never per turn |
| `agents/` | 10 subagents (9 custom + the platform-native `Explore` override). `tools:` and `model:` are enforced by the host; `allowed-paths:` is not — see the dormancy note in `workflow.md` |
| `commands/` | 11 user-invoked slash commands. All carry `disable-model-invocation: true` |
| `hooks/` | the lifecycle scripts above, plus `.claude/hooks/_hooklib.py` and `.claude/hooks/_projectchecks.py`, which are libraries and not hooks |
| `rules/` | standing constraints loaded every session — pay for them accordingly |
| `output-styles/`, `agent-memory/` | response shape; the durable memory store `tools/memory.py` reads |
| `adapters/`, `portability/` | host capability mappings and the fail-safe portability contract; see `adapters/README.md` |
| `audit/` | a pointer, not a second trail — see `audit/README.md` |
| `hooks/state/`, `workflow-state/`, `worktrees/` | runtime residue, gitignored, never installed into a target |

`project-checks.json` is the only place suites are listed. It decides what "the
checks pass" means, so it is the highest-leverage file here.

## Installed into another repository

`install.py` copies this layer anywhere:

    python .claude/install.py --into <dir> --dry-run
    python .claude/install.py --into <dir>

`settings.json` is merged rather than overwritten; `CLAUDE.md` and
`project-checks.json` are never touched. The layer's own ~43 contract suites do
**not** travel — a host runs its own tests, and six shipped validators check the
layer itself. `tools/conftest.py` stops pytest collecting what does ship.

`.claude/layer-manifest.json` records which paths belong to the layer, so a host
measuring its own code does not count the guest.

## When you change something in here

`capability-layer-maintenance` owns this directory and the contracts around it;
`knowledge-manager` owns `LOG.md`, `HANDOFF.md`, `ISSUES.md` and `decisions/`.
Anything you change here is a **control surface**: `tools/scope.py` will call it
risk `high`, which is correct, because it changes what fires for every later
change in every repository the layer reaches.

    python tools/run_checks.py --tier all --require-test
