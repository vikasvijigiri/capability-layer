---
description: Install this capability layer into another repository — copies the skills, agents, hooks and routing, merges settings.json, and adapts .gitignore and ruff
---

Install `.claude/` into a target repo. The script does the copying; your job is
the three judgement calls it cannot make.

## Run it

```bash
python .claude/install.py --into <target> --dry-run   # read this first
python .claude/install.py --into <target>
```

`--dry-run` prints exactly what would change and touches nothing. Read it before
the real run, every time — this writes into a repository that is not this one.

## What it will not do, and why

- **Never overwrites `CLAUDE.md`, `settings.json` or `project-checks.json`.**
  Those carry decisions. A fresh copy would discard them silently.
- **Never copies `hooks/state/`.** Per-session scratch, meaningless elsewhere,
  and committing it once already happened here.
- **Never commits.** The target's own gates decide that.

## Then verify, in the target

```bash
python tools/test_referenced_paths.py   # prose naming things that do not exist
python tools/test_process_router.py     # skills, agents, routing, back-references
python tools/run_checks.py --tier fast  # the project's own lint/typecheck/test
```

The first two are the adjudicators. Do not reason about what ported cleanly —
run them and read what they name.

## Three things to tell whoever owns the target repo

State these plainly. They are surprising, and finding them out by accident is
worse than being told.

1. **The auto-commit commits.** At the end of every turn, without asking, if the
   gates pass. It never pushes.
2. **A repo with no tests cannot auto-commit code** until `"test": false` is set
   in `.claude/project-checks.json`, saying deliberately that there are none.
3. **Every hook is `python …`.** Without Python on PATH they fail silently,
   which is indistinguishable from working.

## After installing

`settings.json` registers every hook the source had. **Remove any that have
nothing to do in the target** — a registered hook whose file is missing exits 2,
and on `PreToolUse` that reads as `deny`, so every shell command fails. The
installer warns about this; it cannot decide it for you.

Then rewrite the target's `CLAUDE.md`. The stub is a starting point and states
the commit loop, the checks and the gotchas — everything else in it is wrong
until someone makes it true.
