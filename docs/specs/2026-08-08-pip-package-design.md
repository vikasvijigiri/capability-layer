# Distributing the capability layer as a pip package — design

**Status:** design, feeding `writing-plans`. Not approved; Gate 1 is the plan.

## The problem

The layer has to be installed into other repositories — starting with one real
product build. Two things block that today, both measured on 2026-08-08:

1. **The only globally-reachable entry point is machine-locked.**
   `~/.claude/commands/install-layer.md` hardcodes
   `C:/Users/VikasVijigiri/Documents/FDE_Vikas/Notes` three times, and the global
   `CLAUDE.md` states that moving or renaming the folder breaks the wiring, with
   Python failing to open a file at session start as the only symptom. The payload
   itself is clean — **zero absolute paths** across `.claude/` and `tools/` — so
   the doorway is the whole problem.

2. **`pyyaml` is imported in three places and declared nowhere.** There is no
   `pyproject.toml`, `setup.py` or `requirements.txt` in the repository. The
   import is caught with a `NOTE` and a `break`, so on a machine without pyyaml
   `test_process_router.py` skips every per-skill frontmatter check and still
   exits 0 — a green that means nothing, which Article V forbids.

## What this is not

**The package is a carrier, not a library.** `.claude/` must live in the target
repository's working tree and be committed there: `settings.json` registers hooks
by path, skills are discovered at `.claude/skills/`, and a team shares them
through version control. Nothing in `site-packages` satisfies any of that.

So `pip install` makes the payload *fetchable* and *versioned*; `uaios install`
copies it into the repo, exactly as `.claude/install.py` does today. Packaging
fixes distribution and upgrade. It changes nothing about runtime.

Rejected alternative: **importable layer** — hooks resolved out of `site-packages`
via `python -m uaios.hooks...`. It removes the copy step and breaks everything
else: the suites resolve `ROOT = parents[1]` and read `.claude/` relative to the
repository, hook commands would carry machine-specific paths, and the team could
no longer read or diff the skills they are governed by. The copy is the feature.

Rejected alternative: **git submodule.** No versioning story anyone enjoys, no
dependency declaration, and it puts a second `.git` inside the product repo.

## Payload

Ships, because the target needs it to run:

- `.claude/skills/`, `agents/`, `commands/`, `hooks/`
- `.claude/workflow.md`, `.claude/constitution.md`
- `AGENTS.md`, `harnesses.json`
- `tools/*.py` — engines **and** suites. The suites travel because they are what
  proves an install worked; `test_install.py` already asserts the installed layer
  passes its own router check in the target.
- `docs/pilots/`, `docs/baselines/` — fixtures two suites read. Omitting them
  reds a clean install, found by running the fast tier in a synthetic target.
- `ruff.toml`, `mypy.ini` — check detection keys off their existence.

Seeded only when absent, never overwritten:

- `.github/workflows/checks.yml`, `CODEOWNERS` — a host's own CI is theirs.

Never ships:

| | Why |
|---|---|
| `CLAUDE.md` | asserts "there is no application code here" and this repo's hook counts. Ships as a **template**. |
| `settings.json` | merged, not copied — a target keeping its own hooks keeps them. |
| `project-checks.json` | repo-specific by definition. Stub generator only; the target states its own `test:` decision. |
| `settings.local.json` | personal, and it grants `Bash(git push:*)`. |
| `.claude/rules/llm-env.md` | mandates groq and a `.env.example` that does not exist. This repository's opinion. |
| `LOG/HANDOFF/ISSUES/TASK/MEMORY.md` | this repository's state. Empty scaffolds only. |
| `decisions/`, `docs/specs/`, `docs/plans/`, `docs/recon/` | content, not layer. |
| `hooks/state/`, `workflow-state/`, `__pycache__` | runtime residue. Already excluded. |
| `Documents/`, `Exercises/`, `node_modules/`, `package.json` | course material, and a manifest that exists only so `npm audit` resolves. |
| `guide/`, `templates/` | 1,978 lines the target never loads. Available as an extra. |

## Console entry points

Replacing `python tools/<x>.py`, which is what forces callers to know a path:

    uaios install [--into DIR] [--dry-run]
    uaios upgrade [--into DIR] [--dry-run]
    uaios verify  [--tier fast|slow|all]
    uaios resume | loop | recon | schedule <plan> | identity

## The three things packaging must fix, that install.py does not

**1. Upgrade silently discards local edits.** `install.py` overwrites any file
whose bytes differ. Once a team customises a skill, re-running it destroys that
work with no warning. `.claude/layer-manifest.json` already records what the layer
owns; it gains a version and a per-file hash of *what was installed*, so upgrade
can classify each file as unchanged, locally-modified, or upstream-changed, and
**refuse to overwrite a locally-modified file without `--force`**.

**2. The undeclared dependency.** `pyyaml` becomes a real dependency, and its
absence must fail rather than skip. A suite that quietly stops checking is worse
than one that is absent.

**3. Seed / merge / preserve is three ad-hoc code paths.** It becomes one
declarative table, so adding a file to the payload is a row rather than a branch.

## Acceptance

- `pip install` into a clean venv, then `uaios install --into <fresh repo>`, then
  the target's own `--tier all` runs green. This is already the standard
  `test_install.py` holds; it must hold through the packaged path.
- `uaios install` twice is idempotent — no file rewritten on the second run.
- A locally-edited skill survives `uaios upgrade` and is reported.
- Every console entry point works from a directory that is not the source repo.
- No absolute path in the built wheel.
- `pip install` in a venv **without** pyyaml fails loudly rather than green.

## Open questions

[NEEDS CLARIFICATION: distribution target — public PyPI, a private index, or
install-from-git (`pip install git+https://github.com/<owner>/<repo>`)? Git needs
no account and no name reservation and is the fastest to a working install;
public PyPI is the only one that makes `pip install uaios` work for anyone.]

[NEEDS CLARIFICATION: package and command name. `uaios` is used throughout this
repo (`refs/uaios/green/`, `UAIOS_AUTOCOMMIT_RUNNING`) and is free-looking but
unchecked on PyPI. Alternatives: `capability-layer`, `claude-sdlc`.]

Python floor is **3.11**, matching `ruff.toml`'s `target-version` and the
`str | None` syntax already used throughout `tools/`. Not marked — it is decided.

Layout keeps `tools/` at the repository root in the target rather than moving it
under a package directory, because every suite resolves `ROOT = parents[1]` and
`.claude/project-checks.json` names `python tools/test_*.py` by path. Not marked
— moving it would be a rewrite of the check contract for no benefit.
