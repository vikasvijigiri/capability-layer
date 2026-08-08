# Pip Package Implementation Plan

**Goal:** Ship the capability layer as an installable, versioned package so it can
be put into a product repository without knowing a filesystem path.

**Source spec:** `docs/specs/2026-08-08-pip-package-design.md`

**Architecture:** Carrier, not library. The wheel holds the payload; `uaios
install` copies it into the target's working tree, which is where `.claude/` has
to live for hooks to resolve and for a team to share it. Runtime is unchanged.

**Tech stack and constraints:** Python 3.11+, `hatchling` backend (no setup.py,
no runtime build step). `pyyaml` becomes a declared dependency. `tools/` stays at
the target repo root — every suite resolves `ROOT = parents[1]` and
`project-checks.json` names `python tools/test_*.py` by path. No absolute paths
may enter the wheel.

## File map

| Path | Action | Responsibility after |
|---|---|---|
| `pyproject.toml` | create | package metadata, `pyyaml` dependency, `uaios` console script, payload as package data |
| `MANIFEST.in` | create | force-include `.claude/**` and `tools/**` into the sdist |
| `uaios/__init__.py` | create | version constant, single source of the version string |
| `uaios/cli.py` | create | argument dispatch to the existing `tools/` and `.claude/install.py` entry points |
| `.claude/install.py` | modify | declarative payload table; manifest v2 with per-file hashes; `upgrade` that refuses to clobber local edits |
| `tools/test_process_router.py` | modify | `pyyaml` absence fails instead of skipping |
| `templates/target-CLAUDE.md` | create | the CLAUDE.md a fresh target gets, asserting nothing about this repo |
| `tools/test_package.py` | create | builds the wheel, installs into a venv, installs into a fresh repo, runs its tier |
| `tools/test_install.py` | modify | cover upgrade, local-edit protection, manifest v2 |
| `.claude/project-checks.json` | modify | register `test_package.py` |
| `README.md` | modify | install instructions; fix the stale "thirteen skills" and the linear entry diagram |

---

## Tasks

### Task 1: Package metadata

**Purpose:** `python -m build` produces a wheel containing the whole payload and
declaring its dependency.

**Files:**
- Create: `pyproject.toml` — metadata, deps, console script, package data
- Create: `MANIFEST.in` — sdist inclusion for `.claude/**` and `tools/**`

**Dependencies:** none

**Implementation notes:**
- `[project] requires-python = ">=3.11"`, `dependencies = ["pyyaml>=6"]`.
- `[project.optional-dependencies] dev = ["ruff", "mypy", "build"]`.
- `[project.scripts] uaios = "uaios.cli:main"`.
- hatchling `force-include` maps `.claude` and `tools` into the wheel under
  `uaios/payload/`, so the copier reads them from the installed package.
- Exclude by pattern: `hooks/state`, `workflow-state`, `__pycache__`,
  `settings.local.json`, `project-checks.json`, `CLAUDE.md`, `rules/llm-env.md`.

**Verification:**
- Run: `python -m build --wheel && python -c "import zipfile,sys; z=zipfile.ZipFile(sorted(__import__('glob').glob('dist/*.whl'))[-1]); n=z.namelist(); assert any('payload/.claude/skills/repo-recon/SKILL.md' in x for x in n); assert not any('settings.local' in x or '__pycache__' in x or 'llm-env' in x for x in n); print(len(n),'entries, exclusions honoured')"`
- Expect: a count and `exclusions honoured`

**Done when:** the wheel contains all 14 skills and none of the excluded paths.

### Task 2: Console entry points

**Purpose:** `uaios <verb>` works from any directory, replacing `python tools/x.py`.

**Files:**
- Create: `uaios/__init__.py` — `__version__`, the single source of the version
- Create: `uaios/cli.py` — dispatch to install, upgrade, verify, resume, loop, recon, schedule, identity

**Dependencies:** none

**Implementation notes:**
- Load each target module by path from `uaios/payload/tools/<name>.py` using the
  same `importlib.util.spec_from_file_location` idiom the repo already uses, and
  call its `main(argv)`. Do not re-implement any of them.
- `--into` defaults to the current working directory, never to the payload.
- `uaios --version` prints `__version__`; every other verb forwards its argv.

**Verification:**
- Run: `python -c "from uaios.cli import main; import sys; sys.argv=['uaios','--version']; main([])"`
- Expect: the version string, exit 0

**Done when:** every verb in the spec dispatches and `--version` prints.

### Task 3: pyyaml stops being optional

**Purpose:** a missing dependency fails the suite instead of silently skipping
every per-skill frontmatter check.

**Files:**
- Modify: `tools/test_process_router.py` — the three `import yaml` sites

**Dependencies:** none

**Implementation notes:**
- Import once at module top. On `ImportError`, `check(...)` a failure naming
  `pip install pyyaml` and exit non-zero — do not `break` out of the loop.
- Keep the reason in a comment: the current behaviour prints a NOTE and exits 0
  having checked almost nothing, which Article V forbids.

**Verification:**
- Run: `python -c "import sys; sys.modules['yaml']=None" ; python -m venv /tmp/noyaml && /tmp/noyaml/bin/python tools/test_process_router.py; echo "exit=$?"`
- Expect: non-zero exit and a message naming pyyaml

**Done when:** the suite is red without pyyaml and green with it.

### Task 4: A CLAUDE.md a target can actually keep

**Purpose:** give a fresh target an accurate instruction file instead of this
repository's, which asserts "there is no application code here".

**Files:**
- Create: `templates/target-CLAUDE.md` — the seeded instruction file

**Dependencies:** none

**Implementation notes:**
- Follow `templates/CLAUDE.md`'s existing shape. State the two gates, the commit
  loop, `/verify` before completion claims, and the Never list. Assert **no**
  counts of skills, agents or hooks — those rot, and a wrong count in a target is
  the usual first failure of a copied file.

**Verification:**
- Run: `python -c "t=open('templates/target-CLAUDE.md',encoding='utf-8').read(); import re; assert not re.search(r'(thirteen|fourteen|\b\d+ (skills|agents|hooks))', t), 'asserts a count that will rot'; assert 'no application code here' not in t; print('portable')"`
- Expect: `portable`

**Done when:** the template asserts nothing instance-specific.

### Task 5: install.py gains a payload table and a safe upgrade

**Purpose:** stop `install` silently overwriting a customised skill, and make the
payload one declarative table.

**Files:**
- Modify: `.claude/install.py` — payload table, manifest v2, `upgrade`

**Dependencies:** none

**Implementation notes:**
- One `PAYLOAD` table of `(pattern, policy)` where policy is
  `copy | seed | merge | preserve | skip`, replacing `TREES`/`FILES`/`SEED`/
  `PRESERVE`/`MERGE`/`SKIP_PARTS`.
- Manifest gains `version` and `files: {path: sha256-at-install}`.
- `upgrade` classifies each payload file: **unchanged** (hash matches) → copy;
  **locally modified** (differs from recorded hash) → report and skip unless
  `--force`; **new** → copy. Print a count per class; never overwrite a local
  edit silently.

**Verification:**
- Run: `python tools/test_install.py`
- Expect: `All install tests passed`

**Done when:** an edited skill survives `upgrade` and is named in its report.

### Task 6: Prove the packaged path end to end

**Purpose:** the acceptance criterion — a wheel, a venv, a fresh repo, a green tier.

**Files:**
- Create: `tools/test_package.py` — build, install, install-into, verify
- Modify: `tools/test_install.py` — upgrade and local-edit cases

**Dependencies:** 1, 2, 5

**Implementation notes:**
- Build the wheel into a temp dir, `venv` + `pip install <wheel>`, run
  `uaios install --into <fresh git repo>`, then run the target's
  `python tools/run_checks.py --tier all --require-test` and require green.
- Assert no absolute path appears in any text file in the wheel.
- Skip with a printed NOTE, not a pass, if `build` or network is unavailable —
  and make the skip visible in the output.

**Verification:**
- Run: `python tools/test_package.py`
- Expect: `All package tests passed`, including the target's own green tier

**Done when:** the packaged path reproduces the 30-check green in a fresh repo.

### Task 7: Register and document

**Purpose:** the new suite runs in the tier, and README stops being wrong.

**Files:**
- Modify: `.claude/project-checks.json` — register `test_package.py`
- Modify: `README.md` — install instructions; fix "thirteen skills" and the entry diagram

**Dependencies:** 6

**Implementation notes:**
- README currently says "the thirteen skills" (there are 14) and draws
  `task-brief → brainstormer → writing-plans` as a linear chain, which contradicts
  `workflow.md`'s Entry section where the first two are alternatives.
- Add the `pip install` / `uaios install` path as the documented entry.

**Verification:**
- Run: `python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 31 check(s) green`

**Done when:** the tier is green with the new suite registered.

---

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [ ] II Test first — Tasks 1, 2, 4, 5 are packaging and configuration whose
      failing test is the verification command itself; Task 6 is the executable
      proof and is written before Task 7 depends on it. Stated rather than ticked.
- [x] III Smallest change — no refactor beyond the payload table Task 5 requires
- [x] IV Reversibility — nothing published; `pip install` target is an open
      question and no push, tag or upload is in this plan
- [x] V No silent degradation — Task 3 exists precisely to remove one
- [x] VI Mechanism over rule — the local-edit guard is a hash check, not a warning
- [x] VII Secrets never land — `settings.local.json` is excluded from the payload
      by pattern and asserted in Task 1's verification

## Risks and rollback

- **The wheel could ship an absolute path.** Task 6 asserts against it. Rollback
  is deleting `dist/`; nothing is published by this plan.
- **`force-include` behaviour differs across hatchling versions.** Task 1's
  verification reads the built wheel rather than trusting the config.
- **Registering a slow suite in the fast tier would tax every turn.**
  `test_package.py` builds a wheel and creates a venv; if it exceeds a few
  seconds it belongs in the slow tier, and Task 7 must place it accordingly.


## Approved 2026-08-08

Gate 1 passed. Execution mode: subagent, round 1 dispatched as five concurrent
`task-implementer` agents per `tools/parallel_groups.py`. Both clarifications
resolved above; none remain open.
