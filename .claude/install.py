#!/usr/bin/env python3
"""Install this capability layer into another directory.

    python .claude/install.py --into ../other --dry-run
    python .claude/install.py --into ../other

Why this file exists at all
---------------------------
It did not, until 2026-08-07. `~/.claude/commands/install-layer.md` and the
global `CLAUDE.md` had documented `.claude/install.py` for days, the audit went
looking for it, and there was nothing there. Both references live outside the
repository, so `tools/test_referenced_paths.py` -- which is repo-scoped -- could
never have caught it. The layer's single most-repeated failure is a name in prose
that resolves to nothing, and its own entry point was an instance of it.

Three rules, each because a fresh copy would otherwise discard a decision:

  PRESERVE  an existing `CLAUDE.md` and `.claude/project-checks.json` are never
            overwritten. A missing `CLAUDE.md` receives only a small bootloader
            that imports `AGENTS.md`; a source copy asserting this repo's facts
            is worse than no file at all.
  MERGE     `.claude/settings.json` is unioned by hook command string, so a
            target keeping its own hooks keeps them.
  SKIP      `__pycache__`, `.claude/hooks/state/`, and `.claude/workflow-state/`
            are runtime residue, not layer.

`--dry-run` writes nothing and prints every path it would touch. Run it first.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]

# Directories copied whole.
TREES = (
    ".claude/skills",
    ".claude/agents",
    ".claude/commands",
    ".claude/hooks",
    ".claude/rules",
    ".claude/output-styles",
    ".claude/workflows",
    ".claude/policies",
    ".claude/agent-memory",
    "tools",
    # Fixtures the suites read. `test_pilot_contract.py` and `test_recon.py` are
    # part of the layer, so their inputs are too -- installing the checks without
    # what they consume produced five red suites in a freshly installed target,
    # found by installing into a synthetic repo on 2026-08-07 and running them.
    "docs/pilots",
    "docs/baselines",
    # The authoring documentation the layer's OWN suites and skills cite by path.
    # Neither shipped until 2026-08-08, and the failure surfaced only in a target:
    # `test_hook_standards.py`'s docstring opens "Check repository hooks against
    # guide/how_to_create_hooks.md", `test_process_router.py` quotes
    # `guide/how_to_create_subagents.md` and `templates/Skills.md` as the source of
    # two rules, and `capability-layer-maintenance` tells the model to compare a
    # new hook or skill against `templates/` and `guide/`. In an installed repo
    # every one of those resolved to nothing.
    #
    # `test_referenced_paths.py` could not catch it twice over: it scans `.md`
    # files, so citations in `.py` docstrings are invisible to it, and it is
    # repo-scoped, so the `.md` citations resolve here where `guide/` exists.
    # 124KB together -- cheap against a skill telling somebody to read a directory
    # that is not there.
    "guide",
    "templates",
    # The host-neutral capability contract and its per-host adapter bindings.
    # `AGENTS.md` and `harnesses.json` both ship and both promise these paths
    # exist in every install ("`.claude/portability/capabilities.json` defines
    # the host-neutral capabilities the workflow requires; `.claude/adapters/`
    # binds each declared host"), and `capability-layer-maintenance` tells the
    # model to run `tools/test_portability_contract.py` after an adapter change
    # -- a suite that reads exactly these five files. Shipping the suite without
    # its data left every installed target with a mandated command that exits on
    # a missing file. 5 files, ~200 lines.
    ".claude/portability",
    ".claude/adapters",
)

# Single files copied as-is when absent or stale.
FILES = (
    ".claude/workflow.md",
    ".claude/constitution.md",
    # Itself. Without this the target cannot install the layer anywhere else, and
    # `test_install.py` -- which travels -- fails on its own first assertion.
    ".claude/install.py",
    "AGENTS.md",
    "harnesses.json",
    # AGENTS.md points a bridging non-Claude host here for the exact hook
    # invocation contract. Unlike guide/ and templates/ (authoring references
    # for someone changing the layer), this is operational documentation a
    # TARGET needs, so it ships as a file rather than living only in docs/.
    "docs/harness-hook-bridge.md",
)

# Written only when absent, never overwritten, but not in PRESERVE because a
# target that has none should get one. A host's own CI workflow is theirs; the
# layer's is a starting point that calls the same resolver `/verify` does, so the
# two cannot drift.
SEED = (
    ".github/workflows/checks.yml",
    # A target's lint and typecheck configuration is ITS decision, and these were
    # in FILES until 2026-08-08 -- copied unconditionally, so installing the layer
    # silently overwrote a product's tuned `ruff.toml` with this repository's.
    # Seeded instead: a repo with none gets a working starting point, a repo with
    # its own keeps every rule in it.
    "ruff.toml",
    "mypy.ini",
    # Seeded from `templates/CODEOWNERS.seed`, never from this repository's own
    # copy -- see `SEED_SOURCE`. It used to be justified by `test_ci_shape.py`
    # asserting it "and it travels with the layer"; that stopped being true when
    # the internal suites were removed from the payload on 2026-08-16, so the
    # reason it stays is the ownership file itself: a workflow seeded with no
    # ownership beside it is a gate nobody is named on.
    "CODEOWNERS",
)

# A seeded file whose payload lives somewhere other than the same path here.
#
# `CODEOWNERS` is the case that forced it. Seeding the copy at this repository's
# root shipped a real GitHub handle into every target as owner of `*`, where it
# either requests review from a stranger on every pull request or -- worse --
# silently does nothing, because GitHub ignores an owner who is not a
# collaborator. The file still LOOKS like governance either way, which is the
# failure mode that matters. `templates/CODEOWNERS.seed` carries the same
# path-scoped rules with a placeholder and says on its first line to replace it.
SEED_SOURCE = {"CODEOWNERS": "templates/CODEOWNERS.seed"}

# Seeded only into a target that already has Python of its own.
#
# Both are markers in `_projectchecks.MARKER_CHECKS`, so seeding them decides
# what the HOST's checks are, not just what the layer's are. Measured
# 2026-08-16: a Node-only repository resolved four fast checks after install,
# two of them `ruff check .` and `mypy` that it never asked for and that pass
# only while the layer's own Python happens to be clean.
PYTHON_SEED = {"ruff.toml", "mypy.ini"}

CLAUDE_SEED = "@AGENTS.md\n\n# Capability layer\n\nThis repository uses the portable layer in `.claude/`. Read `.claude/workflow.md` for the execution policy and use the native skills, commands, and hooks registered by the active host.\n"

# Never overwritten. Each carries a decision a fresh copy would silently discard.
PRESERVE = (
    "CLAUDE.md",
    ".claude/project-checks.json",
)

# Merged rather than replaced.
MERGE = (".claude/settings.json",)

# Runtime residue. Copying it would import this repo's attempt counters and
# green refs into a repository they say nothing true about.
SKIP_PARTS = {"__pycache__", ".pytest_cache", "state", "workflow-state"}

# Written when the target has no project-checks.json. `test: false` is NOT set
# here on purpose: a repo with no tests must state that deliberately, because
# "the tests passed" and "there were none" are different facts and the
# auto-commit gate distinguishes them.
CHECKS_STUB = {
    "_note": (
        "What `the checks pass` means in THIS repository. Read by "
        ".claude/hooks/_projectchecks.py, which the auto-commit gates on and "
        "which /verify calls. A key takes a command string, a list of them, or "
        "false to disable that kind as a stated decision. An absent key means "
        "detect it. Written by .claude/install.py; edit it rather than deleting it."
    ),
    "_first_decision": (
        "If this repository has no tests, set \"test\": false and say why. Until "
        "then the auto-commit refuses any change containing code, because a "
        "passing check and an absent one are not the same evidence."
    ),
    "timeout": 300,
    "max_files": 25,
}


# Individual files inside an otherwise-shipping tree that must not travel.
#
# `SKIP_PARTS` matches whole directory components, which cannot express "this one
# file". `.claude/rules/` is a payload tree and should be — a target wants the
# rules mechanism — but `llm-env.md` is THIS repository's opinion: it mandates
# groq and `opengpt oss 120B` for language-model workflows that do not exist here,
# and a root `.env.example` that does not exist either. Installing an unenforced
# mandate into somebody else's repo is worse than shipping nothing, because it
# loads every session and reads as policy.
#
# Found by auditing a built wheel, not by reading this file.
EXCLUDE_FILES = (
    ".claude/rules/llm-env.md",
)

# The only `tools/test_*.py` a host has any use for: they check that the layer
# it just INSTALLED is intact and wired. `install.py` ends by telling the reader
# to run the first two.
#
# Everything else under that glob tests the layer's own internals -- the check
# runner, the resume state machine, the escalation ladder, the packaging -- and
# a host has no more use for those than for this repository's git history.
#
# The split is 6 files against 36, 119KB against 418KB, and shipping the 36 was
# actively harmful rather than merely wasteful. Measured 2026-08-16 in a fresh
# Python product:
#
#     INTERNALERROR> .../product/tools/test_package.py line 109: sys.exit(0)
#     no tests ran in 32.16s
#
# They are standalone scripts that `sys.exit()` at import, pytest collected them
# during its own run, and the HOST'S suite never executed. Installing the layer
# broke the host's test runner. Nothing caught it because every one of
# `test_install.py`'s 102 assertions checked installation mechanics and none
# checked that the installed layer works.
#
# Verified against the runtime before cutting: no non-test tool imports any test
# module, so nothing the layer DOES depends on them.
#
# The list is not "the ones that happen to be safe" -- it is every suite a
# SHIPPED skill or command instructs the reader to run. A shipped skill naming a
# suite that is not here is the same silent break as a dangling hook path, and
# `test_referenced_paths.py` (now run in the target by `test_install.py`) fails
# on it. `test_doc_entries.py` is `documentation`'s mandatory LOG/ISSUES-entry
# validator and reads only those two files; `test_portability_contract.py` is
# `capability-layer-maintenance`'s adapter check and reads the `.claude/adapters`
# and `.claude/portability` trees now added to TREES.
SHIPPED_SUITES = frozenset({
    "test_process_router.py",
    "test_referenced_paths.py",
    "test_command_standards.py",
    "test_agent_standards.py",
    "test_hook_registration.py",
    "test_workflow_contract.py",
    "test_doc_entries.py",
    "test_portability_contract.py",
})


def is_internal_suite(rel: Path) -> bool:
    """True for a layer self-test the host has no use for."""
    return (rel.parent.as_posix() == "tools"
            and rel.name.startswith("test_")
            and rel.name.endswith(".py")
            and rel.name not in SHIPPED_SUITES)


def skipped(rel: Path) -> bool:
    if rel.as_posix() in EXCLUDE_FILES:
        return True
    if is_internal_suite(rel):
        return True
    return any(part in SKIP_PARTS for part in rel.parts)


# Files that travel in a distribution but are not in TREES/FILES/SEED, because
# their install policy is not "copy".
#
# `.claude/settings.json` is the one that matters. It is MERGED into a target
# rather than copied, so it never lands verbatim -- but the merge needs a source
# to merge FROM, so it must be in the payload. The spec said "never ships", which
# was ambiguous enough to have broken every install silently: an empty merge
# registers no hooks and raises nothing.
EXTRA_PAYLOAD = (
    ".claude/settings.json",
    "README.md",
)


def payload_files(source: Path = SOURCE) -> list[Path]:
    """Every repo-relative path that belongs in a distribution of this layer.

    **One owner, and it has to be.** This list existed twice for one build --
    here, and as an `exclude` list in `pyproject.toml` -- and hatchling's
    `force-include` ignores `exclude` entirely, so "force" meant force. The first
    wheel shipped `.claude/settings.local.json`, which grants `Bash(git push:*)`,
    along with `project-checks.json` and this repository's runtime hook state.

    Nothing detected it: the wheel built cleanly and installed cleanly. It was
    caught by a verification that reads the built artifact instead of trusting the
    configuration that produced it, which is the only kind of check that can catch
    a packaging bug at all.

    `PRESERVE` is deliberately absent. `CLAUDE.md` asserts facts true only in the
    repository that wrote it, and `project-checks.json` states what "the checks
    pass" means there; a target gets a stub and a template, never these.
    """
    out: list[Path] = []
    for tree in TREES:
        out.extend(iter_tree(source, tree))
    for name in (*FILES, *SEED, *EXTRA_PAYLOAD):
        rel = Path(name)
        if (source / rel).is_file() and not skipped(rel):
            out.append(rel)
    # Deduplicated and ordered so two runs produce byte-identical staging.
    return sorted({p.as_posix(): p for p in out}.values(),
                  key=lambda p: p.as_posix())


def iter_tree(root: Path, tree: str) -> list[Path]:
    """Every file under `tree`, relative to `root`, runtime residue excluded."""
    base = root / tree
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if skipped(rel):
            continue
        out.append(rel)
    return out


def merge_settings(source_text: str, target_text: str) -> tuple[str, list[str]]:
    """Union the two hook registries by command string.

    Returns the merged JSON and one note per hook actually added. A target that
    registers its own hooks keeps every one of them: this only ever adds.

    Both sides are parsed, never string-spliced -- a stray comma in
    settings.json silently turns the entire hook layer off, which is the one
    failure in this layer with no symptom at all.
    """
    notes: list[str] = []
    try:
        src = json.loads(source_text)
    except ValueError as exc:
        raise SystemExit(f"source settings.json is not valid JSON: {exc}") from exc
    try:
        dst = json.loads(target_text) if target_text.strip() else {}
    except ValueError as exc:
        raise SystemExit(
            f"target settings.json is not valid JSON, so it cannot be merged "
            f"safely: {exc}. Fix or move it, then re-run."
        ) from exc

    src_hooks = src.get("hooks") or {}
    dst_hooks = dst.setdefault("hooks", {}) if isinstance(dst, dict) else {}

    for event, blocks in src_hooks.items():
        existing = dst_hooks.setdefault(event, [])
        have = {
            h.get("command")
            for block in existing if isinstance(block, dict)
            for h in (block.get("hooks") or []) if isinstance(h, dict)
        }
        for block in blocks:
            fresh = [
                h for h in (block.get("hooks") or [])
                if isinstance(h, dict) and h.get("command") not in have
            ]
            if not fresh:
                continue
            new_block = {k: v for k, v in block.items() if k != "hooks"}
            new_block["hooks"] = fresh
            existing.append(new_block)
            for h in fresh:
                notes.append(f"{event}: {Path(str(h.get('command'))).name}")

    return json.dumps(dst, indent=2) + "\n", notes


def _layer_owned(target: Path) -> set[str]:
    """Paths a previous install recorded as the layer's, or empty."""
    try:
        data = json.loads((target / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    paths = data.get("paths") if isinstance(data, dict) else None
    return {str(p).replace("\\", "/") for p in paths} if isinstance(paths, list) else set()


def _layer_hashes(target: Path) -> dict[str, str]:
    """`{path: sha256}` recorded at the last install, or empty.

    Empty is the honest answer for a v1 manifest and makes `upgrade` fall back to
    refusing every difference -- over-cautious rather than silently overwriting a
    file it has no baseline for.
    """
    try:
        data = json.loads((target / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict):
        return {}
    return {str(k).replace("\\", "/"): str(v) for k, v in files.items()}


def _noise(path: Path, root: Path) -> bool:
    parts = set(path.relative_to(root).parts)
    return bool(parts & {"node_modules", ".venv", "venv", "dist", "build",
                         "__pycache__", "target", "vendor", ".git"})


def seed_source(name: str) -> Path:
    """Where a seeded file's payload is read from. See `SEED_SOURCE`."""
    return SOURCE / SEED_SOURCE.get(name, name)


def target_has_python(target: Path) -> bool:
    """Does the TARGET have Python of its own, discounting the layer's?

    Called from `plan()`, before `apply()` copies anything, because after that
    the answer is always yes -- `tools/` alone is 26 Python files. On a REPEAT
    install the layer's files are already on disk, so `_layer_owned()` is what
    keeps the answer about the host; it is the same manifest discriminator that
    stops `_projectchecks` adopting the layer's suites as the host's tests, and
    it fails open to an empty set, which over-seeds rather than under-detects.
    """
    owned = _layer_owned(target)
    for path in target.rglob("*.py"):
        if _noise(path, target):
            continue
        if path.relative_to(target).as_posix() in owned:
            continue
        return True
    return False


def entry_point(target: Path) -> str:
    """Where the chain should start in the target, from what is already there.

    Deliberately shallow: this is a deterministic script, not the session. It
    reports a signal and names the skill that consumes it. Deciding what the
    work actually is belongs to `repository-navigation`, which can read code.
    """
    has_git = (target / ".git").exists()
    has_plan = any((target / "docs" / "plans").glob("*.md")) \
        if (target / "docs" / "plans").is_dir() else False
    has_task = (target / "TASK.md").is_file()

    # The layer's own files are not the host's code. `main` also calls this BEFORE
    # writing anything, so the dry run and the real run describe the same target
    # -- they disagreed until 2026-08-07 ("empty, start at framing" then "an
    # existing codebase" for one unchanged repo), because the second reading
    # counted the ~33 tool scripts the first one had just installed.
    owned = _layer_owned(target)
    tracked = sum(
        1 for suffix in ("*.py", "*.ts", "*.js", "*.tsx", "*.go", "*.rs", "*.rb")
        for p in target.rglob(suffix)
        if not _noise(p, target) and p.relative_to(target).as_posix() not in owned
    )

    if not has_git:
        return ("not a git repository -- `git init` first, or the auto-commit, "
                "branch guard and every derived state have nothing to read")
    if has_plan:
        return "docs/plans/ already has a plan -- run `python tools/resume.py`"
    if tracked > 20:
        return ("an existing codebase with no plan -- start at "
                "`repository-navigation`, which reads the repo and writes the brief")
    if has_task:
        return "TASK.md exists -- resume `task-analysis` at its planning stage"
    return "empty or near-empty -- start at `task-analysis`"


def plan(target: Path) -> tuple[list[tuple[Path, str]], list[str]]:
    """Every (relative path, action) this install would perform, plus warnings.

    Pure with respect to the target: it reads, never writes. `main` renders this
    for --dry-run and executes exactly the same list otherwise, so the two can
    never describe different installs.
    """
    actions: list[tuple[Path, str]] = []
    warnings: list[str] = []

    for tree in TREES:
        for rel in iter_tree(SOURCE, tree):
            dst = target / rel
            if not dst.exists():
                actions.append((rel, "create"))
            elif dst.read_bytes() != (SOURCE / rel).read_bytes():
                actions.append((rel, "overwrite"))
            else:
                actions.append((rel, "unchanged"))

    for name in FILES:
        src = SOURCE / name
        if not src.is_file():
            warnings.append(f"source is missing {name} -- not copied")
            continue
        dst = target / name
        if not dst.exists():
            actions.append((Path(name), "create"))
        elif dst.read_bytes() != src.read_bytes():
            actions.append((Path(name), "overwrite"))
        else:
            actions.append((Path(name), "unchanged"))

    host_python = target_has_python(target)
    for name in SEED:
        if name in PYTHON_SEED and not host_python:
            warnings.append(f"{name} not seeded -- this target has no Python of "
                            f"its own, and seeding it would add a Python check "
                            f"to the host's own tier")
            continue
        src = seed_source(name)
        if not src.is_file():
            warnings.append(f"source is missing {name} -- not seeded")
            continue
        dst = target / name
        actions.append((Path(name), "preserve" if dst.exists() else "create"))

    claude = target / "CLAUDE.md"
    actions.append((Path("CLAUDE.md"), "preserve" if claude.exists() else "create-claude-stub"))

    for name in PRESERVE:
        dst = target / name
        if dst.exists():
            actions.append((Path(name), "preserve"))
        elif name == ".claude/project-checks.json":
            actions.append((Path(name), "create-stub"))
        else:
            actions.append((Path(name), "skip-absent"))

    for name in MERGE:
        actions.append((Path(name), "merge"))

    return actions, warnings


MANIFEST = Path(".claude") / "layer-manifest.json"
MANIFEST_VERSION = 2


def file_hash(path: Path) -> str:
    """sha256 of a file's bytes, or '' when it cannot be read.

    Content, not mtime. A checkout, a clone or a `touch` all move mtime without
    changing a byte, and an upgrade that refused on mtime would refuse on every
    fresh clone.
    """
    import hashlib
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def write_manifest(target: Path, actions: list[tuple[Path, str]]) -> int:
    """Record exactly which paths belong to the layer rather than to the host.

    Without this, every measurement of the host repository counts the guest.
    Installing into a one-file service made `tools/recon.py` report 25 test files
    over 26 code files, `install.py` contradict its own dry run about whether the
    target was empty, and `resume.py` sit one commit away from sending a two-file
    repo into RECON.

    Recorded rather than pattern-matched: a host may have its own `tools/`, and
    the installer merges into it, so `tools/*` is not a safe exclusion. What is
    safe is the list of paths this installer actually wrote.

    `PRESERVE` files are excluded -- a `CLAUDE.md` the host already had is the
    host's, and one it did not is not written at all.
    """
    owned = sorted({
        rel.as_posix() for rel, action in actions
        if action in ("create", "overwrite", "unchanged", "create-stub", "create-claude-stub", "merge")
        and rel.as_posix() not in PRESERVE
    } | {MANIFEST.as_posix()})
    # The hash of what was INSTALLED, per file. This is what lets `upgrade` tell
    # "the team edited this" from "upstream changed it" -- without it the only
    # safe reading of any difference is "local edit", so every genuine upstream
    # improvement is refused too. Recorded from the source at install time, not
    # from the target, so a file that fails to copy does not get a hash claiming
    # it succeeded.
    # `seed_source` and not `SOURCE / rel`: a `SEED_SOURCE` file is installed
    # from a template, so hashing the same-named file at this repository's root
    # would record a hash the target never had -- and `upgrade` would read that
    # difference as a local edit and refuse every later improvement to it.
    hashes = {
        rel: (file_hash(seed_source(rel)) if rel != "CLAUDE.md"
              else __import__("hashlib").sha256(CLAUDE_SEED.encode()).hexdigest())
        for rel in owned
        if rel != MANIFEST.as_posix() and (rel == "CLAUDE.md" or seed_source(rel).is_file())
    }

    path = target / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "version": MANIFEST_VERSION,
        "files": hashes,
        "_why": (
            "Paths owned by the capability layer, not by this repository. Read by "
            "_hooklib.layer_paths() so that tools/recon.py and tools/resume.py "
            "measure the host's code rather than the layer's. Delete this file "
            "and every such measurement silently includes ~50 of the layer's own "
            "files. Rewritten by .claude/install.py on each install."
        ),
        "paths": owned,
    }, indent=2) + "\n", encoding="utf-8")
    return len(owned)


def apply(target: Path, actions: list[tuple[Path, str]]) -> list[str]:
    notes: list[str] = []
    for rel, action in actions:
        dst = target / rel
        if action in ("create", "overwrite"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            # `seed_source` is the identity for everything but the handful of
            # names in SEED_SOURCE, so this stays one copy path rather than two.
            shutil.copy2(seed_source(rel.as_posix()), dst)
        elif action == "create-claude-stub":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(CLAUDE_SEED, encoding="utf-8")
            notes.append("wrote a Claude bootloader importing AGENTS.md")
        elif action == "create-stub":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(json.dumps(CHECKS_STUB, indent=2) + "\n", encoding="utf-8")
            notes.append("wrote a project-checks.json stub -- decide `test` in it")
        elif action == "merge":
            src = SOURCE / rel
            if not src.is_file():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            current = dst.read_text(encoding="utf-8") if dst.exists() else ""
            merged, added = merge_settings(src.read_text(encoding="utf-8"), current)
            dst.write_text(merged, encoding="utf-8")
            notes.extend(f"registered {n}" for n in added)
    owned = write_manifest(target, actions)
    notes.append(f"recorded {owned} layer-owned path(s) in {MANIFEST.as_posix()} -- "
                 f"so the host's own code is measured, not the layer's")
    return notes


def _contained(target: Path, rel: str) -> bool:
    """Is `rel` a path that stays inside `target` once resolved?

    **The manifest is untrusted input.** `.claude/layer-manifest.json` is a
    tracked file: it is committed, it travels with every clone, and `uninstall`
    is most useful precisely on a repository somebody else wrote. Until this
    existed, a manifest carrying `"paths": ["../PRECIOUS.txt"]` made the verb
    delete a file in the target's PARENT directory -- demonstrated against a
    fixture, not theorised, and found by `code-review` after three passes of
    `verifying-work` and an eight-mutation sweep had all reported clean.

    `resolve()` before comparing, because the check has to survive `..`
    segments, an absolute path (`target / "/etc/x"` is `/etc/x` under pathlib
    join semantics), and a symlinked component. `is_relative_to` is the
    containment test; `strict=False` because the path may already be gone.
    """
    try:
        return (target / rel).resolve(strict=False).is_relative_to(target.resolve())
    except (OSError, ValueError):
        return False


def uninstall_plan(target: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    """What an uninstall may remove, must keep, must never touch, and refuses.

    Returns `(remove, kept_edited, kept_protected, refused)`, each a sorted list
    of posix relative paths, and the four are disjoint. Writes nothing --
    applying is `main()`'s job, so a dry run and a real run compute the same
    answer from the same code rather than from two implementations that can
    disagree.

    `refused` holds manifest entries that do not resolve inside the target. They
    are **reported, never silently skipped**: a manifest naming a path outside
    the repository is either corrupt or hostile, and both are things the person
    running a destructive verb needs told. Dropping them quietly would make a
    partial uninstall look complete.

    The rule is `upgrade`'s, with the opposite consequence. `upgrade` compares
    each file's current sha256 against the hash `write_manifest` recorded and
    uses the answer to decide overwrite-vs-keep; this uses it to decide
    delete-vs-keep. One manifest, one comparison, no second notion of ownership.

    The asymmetry that matters: a wrong `upgrade` keeps a file it could have
    refreshed, and a wrong uninstall deletes somebody's work. So every uncertain
    case resolves to keep. A file with no recorded hash -- a v1 manifest, or one
    added after the install -- counts as edited, because "I do not know" and "it
    is unchanged" must not be the same answer.

    `MANIFEST` appears in none of the three lists. The caller removes it last, so
    calling it "kept" would be the report contradicting the tree -- which is
    precisely what the kept-list exists to prevent, and what it did until
    `verifying-work` caught it.

    Three categories are protected outright, and each is read from its own
    constant rather than listed here, so a fourth entry in any of them is
    protected automatically:

    `MERGE`
        `.claude/settings.json` is merged into whatever the host already had, and
        nothing recorded what that was. It is in the manifest because
        `write_manifest` counts `merge` actions -- that is the trap this function
        exists to not fall into. Deleting it destroys hooks nobody can restore.
    `PRESERVE`
        Never written by the installer at all, and already excluded from the
        manifest. Checked anyway: the exclusion lives in `write_manifest` and a
        regression there would otherwise make them deletable.
    `SEED`
        Written only when the target lacked them, which means the repository has
        been running on them ever since. Removing the layer must not also break
        `ruff` and CI in the same step.
    """
    owned = _layer_owned(target)
    if not owned:
        # No manifest, or an unreadable one. Nothing here is provably the
        # layer's, and guessing from directory names is how an uninstaller
        # deletes a host's own `tools/`.
        return [], [], [], []

    recorded = _layer_hashes(target)
    protected_names = {*PRESERVE, *MERGE, *SEED}

    remove: list[str] = []
    kept_edited: list[str] = []
    kept_protected: list[str] = []
    refused: list[str] = []

    for rel in sorted(owned):
        # Containment first, before any other classification. A path that
        # escapes the target must never reach the hash comparison, because a
        # crafted manifest can supply a matching hash for a file it wants gone.
        if not _contained(target, rel):
            refused.append(rel)
            continue
        # The manifest is in NONE of the three lists, and that is the whole
        # correction here. It was in `kept_protected`, so the report printed
        # `kept (yours)  .claude/layer-manifest.json` and `main()` then deleted
        # it -- a report contradicting the tree it describes, which is the exact
        # failure mode the kept-list exists to prevent. It is removed last, by
        # the caller, and reported on its own line.
        if rel == MANIFEST.as_posix():
            continue
        if rel in protected_names:
            kept_protected.append(rel)
            continue

        path = target / rel
        known = recorded.get(rel)
        if not path.is_file():
            # Already gone. Reported as kept rather than removed: the caller's
            # report should describe what it did, and it did not do this.
            kept_edited.append(rel)
            continue
        if known is None or known != file_hash(path):
            kept_edited.append(rel)
            continue
        remove.append(rel)

    return remove, kept_edited, kept_protected, refused


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--into", default=".", help="target directory (default: here)")
    ap.add_argument("--dry-run", action="store_true", dest="dry",
                    help="print every path and write nothing")
    # Mutually exclusive: they are opposite operations over the same manifest,
    # and a run asking for both must fail loudly rather than silently doing half
    # of each. argparse refuses the pair before any path is resolved.
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--upgrade", action="store_true",
                      help="refresh an existing install without discarding local edits")
    mode.add_argument("--uninstall", action="store_true",
                      help="remove the layer's own files, keeping anything edited")
    ap.add_argument("--force", action="store_true",
                    help="with --upgrade, overwrite locally-modified files too")
    args = ap.parse_args(argv)

    target = Path(args.into).resolve()
    if not target.is_dir():
        print(f"no such directory: {target}", file=sys.stderr)
        return 2
    if target == SOURCE or SOURCE in target.parents:
        print(f"refusing: {target} is the source layer or inside it", file=sys.stderr)
        return 2

    # --- uninstall: remove what the layer owns, keep what anyone touched -----
    #
    # Returns before the install machinery below: `plan()` computes what to COPY,
    # and an uninstall has nothing to copy. Sharing that path would mean an
    # uninstall's report was assembled from the install's action list, which is a
    # different question about a different tree.
    if args.uninstall:
        # `--force` means "overwrite local edits" and belongs to `--upgrade`. It
        # does nothing here, and saying so matters more than usual: on a
        # destructive verb it reads as "yes, really delete the kept files too",
        # so a user reaching for it would otherwise get a success exit code and
        # no indication the flag was ignored.
        if args.force:
            print("note: --force has no effect with --uninstall. Files edited "
                  "since install are always kept; delete them yourself if you "
                  "mean to.", file=sys.stderr)

        remove, kept_edited, kept_protected, refused = uninstall_plan(target)

        # "The manifest is missing" and "the manifest classified nothing" are
        # different facts and used to share one message, which sent a reader
        # looking for a file that was sitting in front of them.
        if not _layer_owned(target):
            print(f"no {MANIFEST.as_posix()} in {target} -- nothing here was "
                  f"installed by this layer, and nothing will be removed. "
                  f"Deleting by pattern instead would take the host's own files.",
                  file=sys.stderr)
            return 2
        if not remove and not kept_edited and not kept_protected and not refused:
            print(f"{MANIFEST.as_posix()} in {target} names no removable path -- "
                  f"it exists but lists nothing this can act on.", file=sys.stderr)
            return 2

        # Refused entries are reported BEFORE anything is deleted, and on stderr,
        # because a manifest naming a path outside the repository is either
        # corrupt or hostile and the run should not scroll past it.
        if refused:
            print(f"REFUSED: {len(refused)} manifest entr(ies) resolve outside "
                  f"{target} and will not be touched:", file=sys.stderr)
            for rel in refused:
                print(f"  refused       {rel}", file=sys.stderr)
            print("  A manifest naming paths outside its own repository is "
                  "corrupt or hostile. Nothing outside the target is ever "
                  "removed; check where this repository came from.",
                  file=sys.stderr)

        verb = "would remove" if args.dry else "removed"
        print(f"target {target}\n")
        for rel in remove:
            print(f"  {verb:<13} {rel}")

        # The manifest goes too, and a dry run has to say so. It was announced
        # only on the real run until a no-slop sweep measured the two side by
        # side -- so `--dry-run`, the safety mechanism for a destructive verb,
        # under-reported by exactly the file whose removal makes the verb
        # irreversible. The real run announces it after the deletion succeeds,
        # because there it is a fact rather than an intention.
        if args.dry:
            print(f"  would remove  {MANIFEST.as_posix()}  (last)")

        removed = 0
        if not args.dry:
            for rel in remove:
                path = target / rel
                try:
                    path.unlink()
                    removed += 1
                except OSError as exc:
                    print(f"  FAILED        {rel}: {exc}", file=sys.stderr)

            # Directories the removals emptied. Deepest first, so a parent is
            # considered only after its children are gone; `rmdir` refuses a
            # non-empty directory, which is the guard rather than a check here.
            for d in sorted({(target / rel).parent for rel in remove},
                            key=lambda p: len(p.parts), reverse=True):
                while d != target and d.is_dir():
                    try:
                        d.rmdir()
                    except OSError:
                        break
                    d = d.parent

            # The manifest last. Until it goes the run is resumable, and once it
            # goes a second run refuses instead of guessing -- which is what
            # makes this verb safe to repeat.
            try:
                (target / MANIFEST).unlink()
                print(f"  removed last  {MANIFEST.as_posix()}")
            except OSError:
                pass

        # Every kept file is named. Silence here is the failure mode: the user
        # must know the layer is not fully gone and exactly what is left.
        for rel in kept_edited:
            print(f"  kept (edited) {rel}")
        for rel in kept_protected:
            print(f"  kept (yours)  {rel}")

        print(f"\n{verb} {len(remove) if args.dry else removed} file(s); "
              f"kept {len(kept_edited)} edited, {len(kept_protected)} protected")
        if kept_edited or kept_protected:
            print("Those are yours to delete or keep. Edited files were changed "
                  "after install; protected files are merged configuration, "
                  "preserved documents, or seeded lint/CI config this repository "
                  "has been running on since.")
        if args.dry:
            print("\n--dry-run: nothing was written.")
        return 0

    # Read the target's shape BEFORE writing to it. Otherwise the report describes
    # a repository that now contains the layer, which is not the repository the
    # reader is being told about.
    entry = entry_point(target)

    actions, warnings = plan(target)

    # --- upgrade: never discard a local edit without being told to -----------
    #
    # `install` overwrites any file whose bytes differ from the source. That is
    # right for a first install and wrong for the second: once a team customises
    # a skill, re-running destroys that work silently, and the layer's whole
    # premise is that silent is the worst failure mode available.
    #
    # Three outcomes, decided by comparing the target's CURRENT bytes against the
    # hash recorded when the layer was last installed:
    #
    #   current == recorded   nobody here touched it, so an upstream change is
    #                         safe to take. This is the case a hashless upgrade
    #                         had to refuse, which made it useless for its actual
    #                         purpose -- you upgrade to GET the upstream changes.
    #   current != recorded   somebody edited it. Never overwritten without
    #                         --force, and named either way.
    #   no recorded hash      a v1 manifest, or a file new to the payload. Treated
    #                         as a local edit, because "I do not know" and "it is
    #                         unchanged" must not be the same answer.
    if args.upgrade:
        recorded = _layer_hashes(target)
        kept: list[str] = []
        refreshed: list[str] = []
        added: list[str] = []
        adjusted: list[tuple[Path, str]] = []

        for rel, action in actions:
            posix = rel.as_posix()
            if action != "overwrite":
                if action == "create":
                    added.append(posix)
                adjusted.append((rel, action))
                continue

            known = recorded.get(posix)
            local_now = file_hash(target / rel)
            edited_here = known is None or known != local_now

            if edited_here and not args.force:
                kept.append(posix + ("" if known else "  (no recorded hash)"))
                adjusted.append((rel, "keep-local"))
            else:
                refreshed.append(posix)
                adjusted.append((rel, action))

        actions = adjusted
        source = ("recorded hashes" if recorded
                  else "NO recorded hashes -- a v1 manifest, so every difference "
                       "reads as a local edit")
        print(f"upgrade: {len(added)} new, {len(refreshed)} updated, "
              f"{len(kept)} kept ({source})")
        for rel in kept[:10]:
            print(f"  kept    {rel}")
        if len(kept) > 10:
            print(f"  ...and {len(kept) - 10} more")
        for rel in refreshed[:5]:
            print(f"  updated {rel}")
        if len(refreshed) > 5:
            print(f"  ...and {len(refreshed) - 5} more")
        if kept and not args.force:
            print("  (--force overwrites the kept files; without it they are "
                  "never touched)")
        print()

    counts: dict[str, int] = {}
    for _rel, action in actions:
        counts[action] = counts.get(action, 0) + 1

    verb = "would" if args.dry else "did"
    print(f"source {SOURCE}\ntarget {target}\n")
    for rel, action in actions:
        if action == "unchanged":
            continue
        print(f"  {action:<12} {rel.as_posix()}")

    notes = [] if args.dry else apply(target, actions)

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for warning in warnings:
        print(f"WARNING: {warning}")
    for note in notes:
        print(f"note: {note}")

    print(f"\nentry point: {entry}")
    print(f"\nThree things the target's owner has not opted into, and {verb} happen:")
    print("  1. The auto-commit commits at the end of every turn. It never pushes.")
    print("  2. A repo with no tests cannot auto-commit code until "
          "`\"test\": false` is set in .claude/project-checks.json.")
    print("  3. Every source hook is now registered. Remove any that have nothing "
          "to do here -- a registered hook whose file is missing exits 2, and on "
          "PreToolUse that reads as deny.")
    print("\nThen verify, in the target:")
    print("  python tools/test_referenced_paths.py")
    print("  python tools/test_process_router.py")
    print("  python tools/run_checks.py --tier fast")
    if args.dry:
        print("\n--dry-run: nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
