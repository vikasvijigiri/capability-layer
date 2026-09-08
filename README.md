# Capability Layer

A harness-neutral agent capability layer for software delivery — skills, hooks,
commands and deterministic checks that carry a change from idea to release, with
exactly **two** points a human is asked. There is no application code here; this
repository *is* the layer.

## What it does

| | |
|---|---|
| **Two gates, only two** | the finished plan, and the shipment approval — both asked with `AskUserQuestion`, so approval is a click. Everything between is automated. |
| **Resume from anywhere** | `tools/resume.py` derives state from git facts. Nothing is stored, so nothing goes stale — it survives a cleared context, a crash, a week away. |
| **Enter an unread repo** | `tools/recon.py` maps a codebase into disjoint subsystems and locates what is half-built, so the chain picks up work rather than restarting it. |
| **Bounded self-repair** | `tools/loop.py` classifies a failure before spending on it: infrastructure noise is retried, a real defect gets three attempts, a security finding gets none. |
| **Green is a fact** | every completion claim carries output from a check that actually ran; a check that could not run is *named*, never counted as a pass. |
| **Two check tiers** | fast (lint · typecheck · test) gates every auto-commit in seconds; slow builds the wheel and proves it installs clean. `--tier all --require-test` runs both. |

## Install

```bash
pip install --force-reinstall --no-deps "git+https://github.com/vikasvijigiri/capability-layer"
python -m capability_layer install --into .
```

| Form | Why it is not optional |
|---|---|
| `--force-reinstall --no-deps` | `pyproject.toml` pins `version = 0.1.0` with no per-commit bump, so a plain `pip install` — even `--upgrade` — sees "already installed" and silently keeps the old copy, no error, no warning. `--force-reinstall` re-clones; `--no-deps` skips a redundant `pyyaml` reinstall. |
| `python -m capability_layer`, not the bare command | on a `--user` install (pip cannot write site-packages) the `capability-layer` / `cl` scripts land off PATH on Windows; the module form needs only the interpreter. |

```bash
python -m capability_layer install   --into . --dry-run   # writes nothing, lists every path
python -m capability_layer upgrade   --into .             # keeps files you edited; --force overrides
python -m capability_layer uninstall --into .             # removes only what it installed
python -m capability_layer verify                         # the full tier, in your repo
```

Working from a clone instead: `python .claude/install.py --into <dir>`. Everything
here runs with Python 3.11+ and git alone.

### What lands

| | |
|---|---|
| **Copied** | `.claude/` (skills, agents, commands, hooks), `tools/`, `guide/`, `templates/`, `AGENTS.md`, `harnesses.json` |
| **Seeded only if absent** | `ruff.toml`, `mypy.ini`, `.github/workflows/checks.yml`, `CODEOWNERS` — yours are never overwritten |
| **Merged, never replaced** | `.claude/settings.json` — every hook you already had survives |
| **Never touched** | `CLAUDE.md`, `.claude/project-checks.json` |

- Every file is recorded with a sha256, so `upgrade` and `uninstall` tell **you
  edited this** from **upstream changed this** — an edited file is kept and named,
  never clobbered. Without a `.claude/layer-manifest.json`, `uninstall` refuses
  rather than deleting by pattern, which is what makes a second run safe.
- `.claude/project-checks.json` arrives as a stub with **no `test` key**: a repo
  with no tests must say so (`"test": false` plus a reason), because *tests
  passed* and *there were none* are different facts. Until it is set, the
  auto-commit gate refuses any change containing code.
- **Commit `.claude/` to your repo.** The package is a carrier, not a runtime —
  hooks resolve by path from the working tree, and your team reads the skills
  they are governed by. Nothing is imported from `site-packages` at runtime.
- Hooks fire the moment `.claude/settings.json` is in place — most visibly an
  auto-commit that checkpoints passing work each turn, on a branch, never `main`,
  never pushing. Remove the `post-run` block from `settings.json` to disable it.

Verified end to end from `main` into a fresh repository: 218 payload files land,
the target's own tier returns `PASS: 30 check(s) green (lint, test, typecheck)`,
and none of the files that must never travel do.

## Daily commands

```text
python tools/run_checks.py --tier all --require-test   # is the tree green
python tools/resume.py                                 # where is this work
python tools/recon.py                                  # what is this repo
python tools/loop.py                                   # what to do about a failure
python tools/parallel_groups.py <plan>                 # which tasks may run at once
```

## How a change moves

```text
             ┌──── dispatch, and it returns ────────┐
             │  architecture · research              │
             │  repository-navigation · debugging    │
             ↓                                       │
    task-analysis ───────────────────────────────────┘
      │  frame (six fields) → fetch → plan
      └→ [GATE 1] → implementation → testing → refactoring
                                                   │
   ┌───────────────────────────────────────────────┘
   └→ code-review → release-git (deliver)
                       └→ [GATE 2] → release-git (release) → documentation
```

One door: `task-analysis` frames the request into six fields, dispatches for
whatever it cannot fill (each dispatch returns — not a handoff), then decomposes.
`repository-navigation` runs only for an unread repo; `release-git`'s releasing
procedure only when there is a deploy target; work too small to plan skips the
plan and the gate. `.claude/workflow.md` §Entry owns that rule and is the only
place it is stated. Depth that was once a separate skill now lives in
`<skill>/references/` and loads only when the task calls for it.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/` | the 15 skills, one directory each |
| `.claude/agents/` | 10 subagents — the read-only fan-out set, plus `implementer` and its domain variants `backend-engineer`, `frontend-engineer` |
| `.claude/hooks/` | what fires automatically — checkpoints, secret scan, branch guard, state report |
| `.claude/commands/` | the 16 slash commands, including `/verify`, `/save`, `/publish` |
| `.claude/constitution.md` | seven articles every plan ticks or justifies |
| `.claude/workflow.md` | stage → owner → artefact, the entry rule, and the `[state:*]` blocks the session-start hook renders |
| `.claude/install.py` | copies the layer into another repo; merges `settings.json`, never overwrites a decision |
| `tools/` | `run_checks.py`, `resume.py`, `loop.py`, `recon.py`, `parallel_groups.py`, `scope.py`, `worktree.py`, `security_gate.py`, `bench.py`, and the 53 suites that keep it honest |
| `capability_layer/` | the console entry points; `pyproject.toml` builds the wheel |
| `decisions/` | dated ADRs for the choices that were not obvious |
| `templates/`, `guide/` | how to author a skill, hook, command or workflow here |

## Parallelism is computed, not assumed

`tools/parallel_groups.py` reads each task's declared `Files:` and `Depends on:`
and prints rounds — a round's tasks have disjoint file sets and no dependency
between them. It **refuses a plan rather than guessing**: an undeclared file set
or a prose dependency is unschedulable, because the convenient reading of a
missing dependency is a concurrent dispatch over ordered work. Migrations,
lockfiles and CI config get a round to themselves — the conflict is in the
resource, not the path.

## The rule the rest follows

**Prefer a mechanism to a rule.** A sentence asking the model to remember
something is the weakest thing in this repository; a test or a hook that makes
the mistake impossible is the strongest. Where a rule exists without a mechanism,
it says so. `AGENTS.md` carries the same contract for non-Claude hosts;
`harnesses.json` maps the canonical paths.

## Not proven yet

Stated here rather than discovered later:

| Area | Status |
|---|---|
| End-to-end chain | Completed once — PR #39 ran every stage through `release-git`'s delivering procedure and merged on `main` (`624165c`). Gate 2 and the releasing procedure have never fired: this repo has no deploy target. |
| Parallel dispatch | One read-only subagent has completed a task, so the mechanism is not dead; a **writing** fan-out has never completed a round. The first died because `isolation: worktree` bases on the default branch, not the checked-out one — `parallel-dispatch.md` now states the precondition. |
| Skill trigger rates | `tools/eval_triggers.py` holds 264 queries across the 15 skills, sandboxed and instrument-checked; no live run has been paid for. Across a long session touching every stage, none fired on their own. |
| Slow tier vs. a running system | One member, `tools/test_package.py`. `audit` is `false` by decision and there is no e2e or smoke command, so `tools/smoke.py` has never probed a running process. |

## Authoring

`templates/` and `guide/` show how to author a skill, hook, command or workflow
in this layer. `decisions/` records the non-obvious choices and the options they
beat.
