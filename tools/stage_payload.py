#!/usr/bin/env python3
"""Stage exactly the payload a wheel should carry, into `build/payload/`.

    python tools/stage_payload.py            # stage
    python tools/stage_payload.py --check    # verify a staged tree, write nothing

Why this exists rather than an `exclude` list in `pyproject.toml`
-----------------------------------------------------------------
Hatchling's `force-include` **ignores `exclude`**. "Force" means force. The first
wheel built from this repository carried `.claude/settings.local.json` -- the file
granting `Bash(git push:*)` -- plus `project-checks.json` and this repository's
runtime hook state, while `pyproject.toml` listed every one of them as excluded.
The build reported success and the wheel installed cleanly.

So the exclusion cannot live in the build config. It lives in
`.claude/install.py:payload_files()`, which is already the authority on what the
layer consists of, and this script materialises that answer into a directory the
build config force-includes wholesale. One owner, and the build has nothing left
to get wrong.

The staged tree is disposable and rebuilt from scratch every run, so a file
removed from the payload cannot survive in it from a previous build.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "build" / "payload"

# Anything matching these must never appear in a staged tree. Asserted after
# staging rather than filtered during it: this is the check, not the mechanism,
# and a check that shares its implementation with the thing it checks proves
# nothing. `payload_files()` is what decides; this is what refuses to believe it.
# Matched against whole path COMPONENTS, never as substrings. The first version
# used substrings and refused a clean payload because "worktrees" appears inside
# `references/using-git-worktrees.md` -- a legitimate skill reference. A packaging
# guard that cries wolf gets switched off, which is worse than not having it.
FORBIDDEN_NAMES = frozenset({
    "settings.local.json",   # grants Bash(git push:*)
    "project-checks.json",   # states what "green" means in ONE repository
    "__pycache__",
    "workflow-state",
    "worktrees",
    "llm-env.md",      # this repository's opinion, unenforced and self-violating
    "dist",
    "build",
})
# `state` only when it is the hook runtime directory, not any file called state.



def load_installer():
    path = ROOT / ".claude" / "install.py"
    spec = importlib.util.spec_from_file_location("uaios_install", path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["uaios_install"] = module
    spec.loader.exec_module(module)
    return module


def audit(files: list[str]) -> list[str]:
    """Paths that must not be here. Empty is the only acceptable answer."""
    bad = []
    for rel in files:
        parts = rel.replace("\\", "/").split("/")
        if FORBIDDEN_NAMES & set(parts):
            bad.append(rel)
            continue
        # The hook runtime directory, identified by position rather than by the
        # word "state" appearing anywhere in a path.
        if parts[:3] == [".claude", "hooks", "state"]:
            bad.append(rel)
            continue
        # CLAUDE.md at the payload ROOT asserts facts true only where it was
        # written. A target is seeded from templates/target-CLAUDE.md instead.
        # Nested ones (templates/, docs/) are content and may travel.
        if parts == ["CLAUDE.md"]:
            bad.append(rel)
    return bad


def stage(root: Path, dest: Path) -> tuple[list[str], list[str]]:
    inst = load_installer()
    rels = [p.as_posix() for p in inst.payload_files(root)]

    if dest.exists():
        shutil.rmtree(dest)
    for rel in rels:
        src = root / rel
        if not src.is_file():
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)

    staged = sorted(
        p.relative_to(dest).as_posix()
        for p in dest.rglob("*") if p.is_file()
    )
    return staged, audit(staged)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--dest", default=str(STAGE))
    ap.add_argument("--check", action="store_true",
                    help="audit an existing staged tree and write nothing")
    args = ap.parse_args(argv)

    root, dest = Path(args.root).resolve(), Path(args.dest).resolve()

    if args.check:
        if not dest.is_dir():
            print(f"nothing staged at {dest}", file=sys.stderr)
            return 1
        staged = sorted(p.relative_to(dest).as_posix()
                        for p in dest.rglob("*") if p.is_file())
        bad = audit(staged)
    else:
        staged, bad = stage(root, dest)

    skills = len({s.split("skills/")[1].split("/")[0]
                  for s in staged if "/skills/" in s and s.endswith("SKILL.md")})
    suites = len([s for s in staged if s.startswith("tools/test_")])
    print(f"staged {len(staged)} file(s) -> {dest}")
    print(f"  skills {skills}   suites {suites}   "
          f"hooks {len([s for s in staged if '/hooks/' in s and s.endswith('.py')])}")

    if bad:
        print(f"\nREFUSED: {len(bad)} forbidden path(s) staged:", file=sys.stderr)
        for rel in bad:
            print(f"  - {rel}", file=sys.stderr)
        return 1
    print("  no forbidden path staged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
