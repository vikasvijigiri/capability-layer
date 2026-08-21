#!/usr/bin/env python3
"""Create and remove a git worktree on a base that must be named out loud.

    python tools/worktree.py create unit-a feat/my-branch
    python tools/worktree.py remove unit-a
    python tools/worktree.py list

Why the base is a required positional
-------------------------------------
`HANDOFF.md` at `0c45d2f`: the one fan-out this repository ever attempted failed
because every worktree was based on `main` rather than the working branch. Five
agents wrote correct code against the wrong tree. Nothing errored -- `git
worktree add <path>` with no commit-ish resolves to whatever HEAD happens to be,
and it exits 0.

So `base` is a required positional with no default, and `create()` returns the
resolved base SHA alongside the path. The caller gets the SHA so it can assert
on it -- `git merge-base --is-ancestor <base> <worktree HEAD>` -- rather than
trust that the call succeeding meant the right thing happened. The convenient
default IS the bug; there is no default to omit.

It creates and removes; it decides nothing
------------------------------------------
No branch is pushed, no commit is made, nothing is merged. Worktrees are created
under `<root>/.worktrees/<name>` and `remove()` refuses any name that resolves
outside it, so a crafted name cannot delete elsewhere.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Inside the repository, so `git clean` and a stray `rm -rf` have one place to
# look, and so an abandoned worktree is visible rather than in a temp directory
# nobody checks. Add it to `.gitignore` in the consuming repo if it is not
# already covered.
WORKTREE_DIR = ".worktrees"


class WorktreeError(RuntimeError):
    """A refusal with a stated reason. Never raised for a git failure alone."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, timeout=60)


def _contained(root: Path, name: str) -> Path:
    """Resolve `<root>/.worktrees/<name>` and refuse anything that escapes it.

    Resolution happens BEFORE the comparison, so `..`, a symlink and an absolute
    path are one defect rather than three patterns to enumerate. `Path.resolve`
    on a non-existent path is still lexically correct on both platforms, which is
    what makes this usable for `create` as well as `remove`.
    """
    if not name or name.strip() != name:
        raise WorktreeError(f"refusing worktree name {name!r}: empty or padded")
    holder = (root / WORKTREE_DIR).resolve()
    target = (holder / name).resolve()
    if target == holder or holder not in target.parents:
        raise WorktreeError(
            f"refusing worktree name {name!r}: it resolves to {target}, "
            f"which is outside {holder}")
    return target


def create(root: Path, name: str, base: str, branch: str | None = None) -> tuple[str, str]:
    """Create a worktree for `name` at `base`. Returns (path, resolved base SHA).

    `base` is positional and has no default. See the module docstring.

    `branch`, when given, checks the worktree out onto a NEW named branch at
    `base` instead of detaching -- for the one case a scratch surface is not
    enough: a task whose result must be independently pushable and turned
    into its own PR (a proven-independent round of `tools/parallel_groups.py`).
    Every other caller passes nothing and gets the original, unchanged
    detached behaviour -- this is additive, not a replacement.
    """
    root = Path(root)
    target = _contained(root, name)

    resolved = _git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    if resolved.returncode != 0:
        raise WorktreeError(
            f"refusing to create worktree {name!r}: base {base!r} does not "
            f"resolve -- {resolved.stderr.strip()}")
    sha = resolved.stdout.strip()

    if target.exists():
        raise WorktreeError(
            f"refusing to create worktree {name!r}: {target} already exists")

    target.parent.mkdir(parents=True, exist_ok=True)
    if branch:
        out = _git(root, "worktree", "add", "-b", branch, str(target), sha)
    else:
        # `--detach` because the worktree is a scratch surface for one task, and
        # a named branch per worktree leaves branches behind after teardown. The
        # base is passed explicitly and is the whole point of this function.
        out = _git(root, "worktree", "add", "--detach", str(target), sha)
    if out.returncode != 0:
        raise WorktreeError(
            f"git worktree add failed for {name!r}"
            f"{f' on branch {branch!r}' if branch else ''}: {out.stderr.strip()}")
    return str(target), sha


def remove(root: Path, name: str) -> bool:
    """Remove the worktree. Idempotent: absent is success, not an error.

    Returns True when something was removed.
    """
    root = Path(root)
    target = _contained(root, name)
    if not target.exists():
        # Prune anyway: git keeps administrative metadata for a worktree whose
        # directory was deleted by hand, and that stale entry makes the next
        # `create` with the same name fail for a reason nobody can see.
        _git(root, "worktree", "prune")
        return False
    out = _git(root, "worktree", "remove", "--force", str(target))
    if out.returncode != 0:
        raise WorktreeError(
            f"git worktree remove failed for {name!r}: {out.stderr.strip()}")
    _git(root, "worktree", "prune")
    return True


def listing(root: Path) -> list[str]:
    out = _git(Path(root), "worktree", "list")
    if out.returncode != 0:
        return []
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("create", "remove", "list"))
    ap.add_argument("name", nargs="?")
    # Positional and required for `create`, enforced below rather than by
    # argparse so the error names the reason instead of printing usage.
    ap.add_argument("base", nargs="?")
    ap.add_argument("--root", default=".")
    ap.add_argument("--branch",
                    help="check the worktree out onto this new branch instead "
                         "of detaching -- for a task whose result must be "
                         "independently pushable")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        if args.action == "list":
            for line in listing(root):
                print(line)
            return 0
        if not args.name:
            raise WorktreeError(f"{args.action} needs a worktree name")
        if args.action == "create":
            if not args.base:
                raise WorktreeError(
                    "create needs an explicit base -- there is no default, "
                    "because the default is what made every worktree in the "
                    "one previous fan-out base on the wrong branch")
            path, sha = create(root, args.name, args.base, branch=args.branch)
            print(f"{path}\t{sha}")
            return 0
        removed = remove(root, args.name)
        print("removed" if removed else "absent")
        return 0
    except WorktreeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
