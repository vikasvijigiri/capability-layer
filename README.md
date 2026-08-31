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
pip install --force-reinstall --no-deps "git+https://github.com/vikasvijigiri/capability-layer"
python -m capability_layer install --into .
```

**`--force-reinstall --no-deps` is not optional, and this is not a style
preference — without it you silently get an old copy.** `pyproject.toml`'s
`version` is a fixed `0.1.0` (there is no per-commit version bump), so pip's
own dependency resolver sees "`capability-layer==0.1.0` already installed"
and skips reinstalling — even `pip install --upgrade` alone does this, since
`--upgrade` still short-circuits on a version match. Reproduced live: a
plain `pip install` of this exact URL a second time in the same
environment printed no error and no warning, and left the previous
install's files completely unchanged. `--force-reinstall` is the only flag
that bypasses the version check and actually re-clones and reinstalls;
`--no-deps` keeps it from redundantly reinstalling `pyyaml` every time.

Verified end to end from `main` into a fresh repository: 218 payload files land,
the target's own tier comes back `PASS: 30 check(s) green (lint, test,
typecheck)`, and none of the files that must never travel do.

**`python -m capability_layer`, not the bare command**, unless you know
`Scripts/` is on your PATH. When pip cannot write to site-packages it silently
does a `--user` install, and on Windows those scripts land somewhere PATH does not
look — the package installs, imports, and reports *"the term 'capability-layer' is
not recognized"*. `capability-layer` and `cl` are the same entry point and are
fine when PATH cooperates; the module form needs only the interpreter.

The repository is **private**, so pip needs credentials that can read it.

Already have it installed? `upgrade`, never `install` — the second overwrites
whatever you have edited. The `pip install` line still needs
`--force-reinstall --no-deps` for the same reason as above; `--upgrade`
does nothing extra here and is omitted:

```bash
pip install --force-reinstall --no-deps "git+https://github.com/vikasvijigiri/capability-layer"
python -m capability_layer upgrade --into .
```

The package is a **carrier, not a library**. `.claude/` has to live in your
repository's working tree and be committed there — that is where hooks resolve by
path and where your team reads the skills they are governed by. Nothing is ever
imported from `site-packages` at runtime.

```bash
python -m capability_layer install --into . --dry-run   # writes nothing, lists every path
python -m capability_layer upgrade --into .             # keeps what you edited
python -m capability_layer uninstall --into .           # removes only what it installed
python -m capability_layer verify                       # the full tier, in your repo
```

### Taking it back out

`uninstall` reads the same manifest `upgrade` does and asks the same question —
does this file's sha256 still match what was installed — but uses the answer to
decide delete-vs-keep. It is deliberately timid, because a wrong `upgrade` keeps
a file it could have refreshed and a wrong uninstall deletes your work:

| Kept, and named in the report | Why |
|---|---|
| Anything you edited after install | Your work, not the layer's. A file with no recorded hash counts as edited |
| `.claude/settings.json` | Merged into whatever hooks you already had, and nothing recorded what those were |
| `CLAUDE.md`, `.claude/project-checks.json` | Never written by the installer in the first place |
| Seeded lint and CI config | Written only if you lacked them, so you have been running on them since — removing the layer should not break `ruff` and CI in the same step. The exact set is `SEED` in `.claude/install.py`, and the run names every file it kept |

Everything kept is printed with its reason — silence about a leftover file is the
failure this verb exists to avoid. Run `--dry-run` first; it writes nothing.
Without a `.claude/layer-manifest.json` it refuses outright rather than deleting
by pattern, which is also what makes running it twice safe.

Each install records a sha256 per file, so `upgrade` can tell **you edited this**
from **upstream changed this**: an untouched file takes the update, an edited one
is kept and named, and `--force` is how you say otherwise. Without that
distinction an upgrade either discards your work or refuses every improvement —
there is no safe third behaviour.

Working from a clone instead? `python .claude/install.py --into <dir>` does the
same thing, and everything else here runs with Python 3.11+ and git alone.

### What lands, and what it decides for you

Nothing about your repository. The install writes the layer and gets out of the
way:

| | |
|---|---|
| **Copied** | `.claude/` (skills, agents, commands, hooks), `tools/`, `guide/`, `templates/`, `AGENTS.md`, `harnesses.json` |
| **Seeded only if absent** | `ruff.toml`, `mypy.ini`, `.github/workflows/checks.yml`, `CODEOWNERS` — your own are never overwritten |
| **Merged, never replaced** | `.claude/settings.json` — every hook you already had survives |
| **Never touched** | `CLAUDE.md`, `.claude/project-checks.json` |

`.claude/project-checks.json` arrives as a **stub with no `test` key**, on
purpose. A repository with no tests has to say so deliberately — `"test": false`
with a reason — because *the tests passed* and *there were none* are different
facts, and the auto-commit gate distinguishes them. Until you decide, it refuses
to check in any change containing code.

**Commit `.claude/` to your repository.** The package is a carrier, not a
runtime: hooks resolve by path from the working tree, and your team reads the
skills they are governed by.

Then, in your repo:

```bash
python tools/run_checks.py --tier all --require-test   # what green means here
python tools/resume.py                                 # where is this work
python tools/recon.py                                  # what is this repo
```

**The hooks fire from the moment `.claude/settings.json` is in place** — the most
visible being an auto-commit that checkpoints passing work at the end of every
turn, on a branch, never on `main`, and never pushing. If that is not what you
want, remove the `post-run` block from `settings.json` before your first session.


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
                         ┌──── dispatch, and it returns ─────────┐
                         │  architecture · research               │
                         │  repository-navigation · debugging     │
                         ↓                                        │
                task-analysis ─────────────────────────────────────┘
                  │  frame (six fields) → fetch → plan
                  └→[GATE 1]→ implementation → testing → refactoring
                                                                    │
     ┌──────────────────────────────────────────────────────────────┘
     └→ code-review → release-git (deliver)
                          └→[GATE 2]→ release-git (release) → documentation
```

**The numbers in `workflow.md` are labels, not a sequence.** There is one door:
`task-analysis` frames the request into six fields, dispatches for whatever it
could not fill, then decomposes it. A dispatch is not a handoff — each one comes
back, which is what removed the seam an un-handed-off brief used to fall through.
`repository-navigation` runs only when the repository is unread. `release-git`'s
releasing procedure runs only when there is somewhere to deploy. Work too small
to plan skips the plan and the gate.

`.claude/workflow.md` §Entry owns that rule and is the only place it is stated.
Read it before adding a stage. Each skill states its own triggers and handoff;
depth that used to be a separate skill now lives in `<skill>/references/` and
loads only when the task calls for it.

## Layout

| Path | What it is |
|---|---|
| `.claude/skills/` | the 15 skills, one directory each |
| `.claude/agents/` | 10 subagents — the read-only fan-out set, plus `implementer` and its two domain-grounded variants (`backend-engineer`, `frontend-engineer`) |
| `.claude/hooks/` | what fires automatically — checkpoints, secret scan, branch guard, state report |
| `.claude/commands/` | the 16 slash commands, including `/verify`, `/save` and `/publish` |
| `.claude/constitution.md` | seven articles every plan ticks or justifies |
| `.claude/workflow.md` | stage → owner → artefact, the entry rule, and the `[state:*]` blocks the session-start hook renders |
| `.claude/install.py` | copies the layer into another repository; merges `settings.json`, never overwrites a decision |
| `tools/` | `run_checks.py`, `resume.py`, `loop.py`, `recon.py`, `parallel_groups.py`, `scope.py`, `worktree.py`, `security_gate.py`, `bench.py`, and the 53 suites that keep all of it honest |
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

- **The chain has now completed end to end, once.** Gate 1 has fired 13 times
  as of 2026-08-23 (`python tools/chain.py --ledger`); most of those stopped
  short of delivery. PR #39 (`docs/plans/2026-08-23-ui-ux-design-mcp-skill.md`)
  is the first to run every stage for real — `implementation`, `testing`,
  `refactoring`, `code-review`, and `release-git`'s delivering procedure — and
  land merged on `main` (`624165c`). `release-git`'s *releasing* procedure and
  Gate 2 still have not fired: this repository has no deploy target, so that
  half stays specified and unexercised.
- **Parallel dispatch is diagnosed but still unproven.** One subagent has now
  completed a task correctly — a read-only probe — so the mechanism is not dead.
  What that probe established is why the first fan-out died: `isolation: worktree`
  bases an agent's tree on the repository's **default branch**, not the branch the
  session has checked out, and at the time `main` was the initial commit. The
  round was handed a tree without the work it was asked to extend, and nothing
  reported it, because from inside a worktree a stale base looks like a clean
  checkout. `parallel-dispatch.md` now states the precondition. **A writing
  fan-out has still never completed** — one read-only agent is not a round.
- **Skill trigger rates are unmeasured.** `tools/eval_triggers.py` holds 264
  queries across all 15 skills, sandboxed and instrument-checked; no live run has
  been paid for. "It triggers" rests on description properties the suite enforces,
  not on a measured rate — and the one thing actually observed is that across a
  long session touching every stage, none fired on their own.
- **The slow tier proves the package, and nothing about a running system.** It has
  one member, `tools/test_package.py`. `audit` is `false` by decision and there is
  no e2e or smoke command, so `tools/smoke.py` has still never probed a running
  process.
