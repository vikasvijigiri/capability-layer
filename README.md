# Capability Layer

A harness-neutral agent capability layer for software delivery: skills, hooks,
commands and deterministic checks that carry a change from an idea to a released
one, with exactly two places a human is asked.

There is no application code here. This repository *is* the layer.

## What it does

| | |
|---|---|
| **Two gates, and only two** | the finished plan, and the shipment approval. Both asked with `AskUserQuestion` so approval is a click, not an inference. Everything between them is automated |
| **Resume from anywhere** | `tools/resume.py` derives the state from git facts. Nothing is stored, so nothing goes stale — it survives a cleared context, a crash, a week away |
| **Enter a repo it has never seen** | `tools/recon.py` maps an unread codebase into disjoint subsystems and locates what is half-built, so the chain can pick up work rather than restart it |
| **Bounded self-repair** | `tools/loop.py` classifies a failure before spending anything on it. Infrastructure noise is retried; a real defect gets three attempts; a security finding gets none |
| **Green is a fact, not a claim** | every completion statement is backed by output from a check that actually ran, and a check that could not run is **named** rather than counted as a pass |
| **Two tiers, because cost differs by an order of magnitude** | fast (lint, typecheck, test) gates every auto-commit in seconds; slow builds the wheel and proves it installs into a fresh repo. `--tier all --require-test` runs both |

## Install it into your repo

```bash
pip install git+https://github.com/NG-VikasV/capability-layer
capability-layer install --into .        # `cl` is the same command, shorter
```

The package is a **carrier, not a library**. `.claude/` has to live in your
repository's working tree and be committed there — that is where hooks resolve by
path and where your team reads the skills they are governed by. Nothing is ever
imported from `site-packages` at runtime.

```bash
cl install --into . --dry-run   # writes nothing, prints every path
cl upgrade --into .             # refuses to overwrite anything you edited
cl verify                       # the full tier, in your repo
```

Each install records a sha256 per file, so `upgrade` can tell **you edited this**
from **upstream changed this**: an untouched file takes the update, an edited one
is kept and named, and `--force` is how you say otherwise. Without that
distinction an upgrade either discards your work or refuses every improvement —
there is no safe third behaviour.

Working from a clone instead? `python .claude/install.py --into <dir>` does the
same thing, and everything else here runs with Python 3.11+ and git alone.

## Start here

```text
python tools/run_checks.py --tier all --require-test   # is the tree green
python tools/resume.py                                 # where is this work
python tools/recon.py                                  # what is this repo
python tools/loop.py                                   # what to do about a failure
python tools/parallel_groups.py <plan>                 # which tasks may run at once
```

## How a change moves

```text
                    ┌─ approach settled ──→ do the change ─┐
repo-recon → task-brief                                    ├→ verifying-work
                    └─ approach open ──→ brainstormer ──┐   │
                                                        ↓   │
                                        writing-plans →[GATE 1]→ executing-plans
                                                                        │
     ┌──────────────────────────────────────────────────────────────────┘
     └→ verifying-work → no-slop → code-review → delivering
                                                     └→[GATE 2]→ releasing
                                                                    └→ knowledge-manager
```

**The numbers in `workflow.md` are labels, not a sequence.** `task-brief` and
`brainstormer` are alternatives — one question decides which, *is the approach
settled* — and neither reaches `writing-plans` directly, because six lines is not
a spec. `repo-recon` runs only when the repository is unread. `releasing` runs
only when there is somewhere to deploy.

`.claude/workflow.md` §Entry owns that rule and is the only place it is stated.
Read it before adding a stage. Each skill states its own triggers and handoff;
depth that used to be a separate skill now lives in `<skill>/references/` and
loads only when the task calls for it.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/` | the 14 skills, one directory each |
| `.claude/agents/` | 11 subagents — the read-only fan-out set, plus one implementer |
| `.claude/hooks/` | what fires automatically — checkpoints, secret scan, branch guard, state report |
| `.claude/commands/` | the 12 slash commands, including `/verify`, `/save` and `/publish` |
| `.claude/constitution.md` | seven articles every plan ticks or justifies |
| `.claude/workflow.md` | stage → owner → artefact, the entry rule, and the `[state:*]` blocks the session-start hook renders |
| `.claude/install.py` | copies the layer into another repository; merges `settings.json`, never overwrites a decision |
| `tools/` | `run_checks.py`, `resume.py`, `loop.py`, `recon.py`, `parallel_groups.py`, and the 26 suites that keep all of it honest |
| `capability_layer/` | the console entry points; `pyproject.toml` builds the wheel |
| `decisions/` | dated ADRs for the choices that were not obvious |
| `templates/`, `guide/` | how to author a skill, hook, command or workflow here |

## Parallelism is computed, not assumed

Concurrency is licensed by a property of the plan rather than by judgement.
`tools/parallel_groups.py` reads each task's declared `Files:` and `Depends on:`
and prints rounds; tasks in a round have disjoint file sets and no dependency
between them. It **refuses a plan rather than guessing** — an undeclared file set
or a dependency written as prose is unschedulable, because the convenient reading
of a missing dependency is a concurrent dispatch over ordered work.

Migrations, lockfiles and CI config get a round to themselves: the conflict is in
the resource, not the path.

## The rule the rest follows

**Prefer a mechanism to a rule.** A sentence asking the model to remember
something is the weakest thing in this repository; a test or a hook that makes
the mistake impossible is the strongest. Where a rule exists without a mechanism,
it says so.

`AGENTS.md` carries the same contract for non-Claude hosts, and
`harnesses.json` maps the canonical paths.

## What is not proven yet

Stated here rather than discovered later:

- **The chain has never completed once.** Gate 1 has fired exactly once — on the
  plan that built this package. Gate 2 never has. No approved plan has gone spec →
  release in this repository, so the stages after review are specified and
  unexercised.
- **No subagent has ever completed a task.** The one fan-out — five
  `task-implementer` agents dispatched together, as the scheduler licensed — got
  worktrees based on the initial commit rather than the working branch. Three
  returned `BLOCKED` correctly; two wrote into stranded trees. `isolation:
  worktree` is unverified against *which commit* it bases on, so
  `executing-plans/references/parallel-dispatch.md` documents a mechanism that has
  not yet worked.
- **Skill trigger rates are unmeasured.** `tools/eval_triggers.py` holds 168
  queries across all 14 skills, sandboxed and instrument-checked; no live run has
  been paid for. "It triggers" rests on description properties the suite enforces,
  not on a measured rate — and the one thing actually observed is that across a
  long session touching every stage, none fired on their own.
- **The slow tier proves the package, and nothing about a running system.** It has
  one member, `tools/test_package.py`. `audit` is `false` by decision and there is
  no e2e or smoke command, so `tools/smoke.py` has still never probed a running
  process.
