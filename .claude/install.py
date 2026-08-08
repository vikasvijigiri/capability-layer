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

  PRESERVE  `CLAUDE.md` and `.claude/project-checks.json` are never overwritten.
            One states what the target repository is; the other states what
            "the checks pass" means there. A source copy asserting this repo's
            facts is worse than no file at all.
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
    ".claude/agent-memory",
    "tools",
    # Fixtures the suites read. `test_pilot_contract.py` and `test_recon.py` are
    # part of the layer, so their inputs are too -- installing the checks without
    # what they consume produced five red suites in a freshly installed target,
    # found by installing into a synthetic repo on 2026-08-07 and running them.
    "docs/pilots",
    "docs/baselines",
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
    "ruff.toml",
    "mypy.ini",
)

# Written only when absent, never overwritten, but not in PRESERVE because a
# target that has none should get one. A host's own CI workflow is theirs; the
# layer's is a starting point that calls the same resolver `/verify` does, so the
# two cannot drift.
SEED = (
    ".github/workflows/checks.yml",
    # `test_ci_shape.py` asserts both, and it travels with the layer. Seeding the
    # workflow without the ownership file it is checked against left exactly one
    # red suite in an otherwise-clean install -- found by running the fast tier in
    # a synthetic target rather than by reading either file.
    "CODEOWNERS",
)

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


def skipped(rel: Path) -> bool:
    if rel.as_posix() in EXCLUDE_FILES:
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
    "templates/target-CLAUDE.md",
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


def entry_point(target: Path) -> str:
    """Where the chain should start in the target, from what is already there.

    Deliberately shallow: this is a deterministic script, not the session. It
    reports a signal and names the skill that consumes it. Deciding what the
    work actually is belongs to `repo-recon`, which can read code.
    """
    has_git = (target / ".git").exists()
    has_plan = any((target / "docs" / "plans").glob("*.md")) \
        if (target / "docs" / "plans").is_dir() else False
    has_task = (target / "TASK.md").is_file()

    # The layer's own files are not the host's code. `main` also calls this BEFORE
    # writing anything, so the dry run and the real run describe the same target
    # -- they disagreed until 2026-08-07 ("empty, start at task-brief" then "an
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
        return ("an existing codebase with no plan -- start at `repo-recon`, "
                "which reads the repo and writes the brief")
    if has_task:
        return "TASK.md exists -- start at `writing-plans`"
    return "empty or near-empty -- start at `task-brief`"


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

    for name in SEED:
        src = SOURCE / name
        if not src.is_file():
            warnings.append(f"source is missing {name} -- not seeded")
            continue
        dst = target / name
        actions.append((Path(name), "preserve" if dst.exists() else "create"))

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
        if action in ("create", "overwrite", "unchanged", "create-stub", "merge")
        and rel.as_posix() not in PRESERVE
    } | {MANIFEST.as_posix()})
    # The hash of what was INSTALLED, per file. This is what lets `upgrade` tell
    # "the team edited this" from "upstream changed it" -- without it the only
    # safe reading of any difference is "local edit", so every genuine upstream
    # improvement is refused too. Recorded from the source at install time, not
    # from the target, so a file that fails to copy does not get a hash claiming
    # it succeeded.
    hashes = {
        rel: file_hash(SOURCE / rel)
        for rel in owned
        if rel != MANIFEST.as_posix() and (SOURCE / rel).is_file()
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
            shutil.copy2(SOURCE / rel, dst)
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--into", default=".", help="target directory (default: here)")
    ap.add_argument("--dry-run", action="store_true", dest="dry",
                    help="print every path and write nothing")
    ap.add_argument("--upgrade", action="store_true",
                    help="refresh an existing install without discarding local edits")
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
