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
| **Bounded self-repair** | `tools/loop.py` classifies a failure before spending anything on it. Infrastructure noise is retried; a real defect gets three attempts; a security finding gets none |
| **Green is a fact, not a claim** | every completion statement is backed by output from a check that actually ran |

## Start here

```text
python tools/run_checks.py --tier all --require-test   # is the tree green
python tools/resume.py                                 # where is this work
python tools/loop.py                                   # what to do about a failure
```

No install step. Everything is Python 3.11+ and git.

## How a change moves

```text
task-brief → brainstormer → writing-plans →[GATE 1]→ executing-plans
    → verifying-work → no-slop → code-review → delivering →[GATE 2]→ releasing
    → knowledge-manager
```

`.claude/workflow.md` owns that order and is the file to read before adding a
stage. Each skill states its own triggers and handoff; depth that used to be a
separate skill now lives in `<skill>/references/` and loads only when the task
calls for it.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/` | the thirteen skills, one directory each |
| `.claude/hooks/` | what fires automatically — checkpoints, secret scan, branch guard, state report |
| `.claude/commands/` | slash commands, including `/verify`, `/save` and `/publish` |
| `.claude/constitution.md` | seven articles every plan ticks or justifies |
| `.claude/workflow.md` | stage → owner → artefact, and the `[state:*]` blocks the session-start hook renders |
| `tools/` | `run_checks.py`, `resume.py`, `loop.py`, `analyze.py`, and the suites that keep all of it honest |
| `decisions/` | dated ADRs for the choices that were not obvious |
| `templates/`, `guide/` | how to author a skill, hook, command or workflow here |

## The rule the rest follows

**Prefer a mechanism to a rule.** A sentence asking the model to remember
something is the weakest thing in this repository; a test or a hook that makes
the mistake impossible is the strongest. Where a rule exists without a mechanism,
it says so.

`AGENTS.md` carries the same contract for non-Claude hosts, and
`harnesses.json` maps the canonical paths.
