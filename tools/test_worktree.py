#!/usr/bin/env python3
"""A worktree's base is proved by ancestry, never by the command returning 0.

Why this suite exists
---------------------
`HANDOFF.md` at `0c45d2f`: the only fan-out this repository ever attempted failed
because every worktree was based on `main` rather than the working branch. Five
agents ran, five reported success, and five had written against the wrong tree.
Every `git worktree add` in that run exited 0.

So the property under test is not "the call succeeded". It is
`git merge-base --is-ancestor <base> <worktree HEAD>` -- the only thing that
distinguishes a worktree on the branch you meant from one on the branch you
forgot to name.

Real worktrees in a real temp clone, torn down in a `finally`. Mocking `git`
here would test the mock: the defect being pinned lived in git's own resolution
of an omitted argument, which no fake reproduces.

Run: python tools/test_worktree.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import worktree as wt  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(root), *args],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {out.returncode}: {out.stderr}")
    return out.stdout.strip()


def scratch_repo(root: Path) -> None:
    """Two branches that have diverged, which is what makes the base matter."""
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "base.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    git(root, "checkout", "-q", "-b", "working")
    (root / "work.txt").write_text("work\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "work")
    # `main` moves on, so a worktree silently based on it is detectably wrong
    # rather than merely different.
    git(root, "checkout", "-q", "main")
    (root / "other.txt").write_text("other\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "other")
    git(root, "checkout", "-q", "working")


def main() -> int:
    # --- the signature refuses a default base -------------------------------
    #
    # Asserted on the signature rather than by calling, because "the convenient
    # default IS the bug" is a claim about what a caller can omit. A default
    # added later would keep every behavioural test below green.
    import inspect
    sig = inspect.signature(wt.create)
    base_param = sig.parameters.get("base")
    check("create() takes a base", base_param is not None, str(sig))
    check("create()'s base has no default",
          base_param is not None and base_param.default is inspect.Parameter.empty,
          f"default is {base_param.default!r}" if base_param else "no parameter")

    tmp = Path(tempfile.mkdtemp(prefix="wt-test-"))
    try:
        root = tmp / "repo"
        root.mkdir()
        scratch_repo(root)
        working_sha = git(root, "rev-parse", "working")

        # --- the base is what was named, proved by ancestry ------------------
        path, sha = wt.create(root, "unit-a", "working")
        check("create() returns a path that exists", Path(path).is_dir(), path)
        check("create() returns the resolved base SHA", sha == working_sha,
              f"{sha} != {working_sha}")

        rc = subprocess.run(
            ["git", "-C", path, "merge-base", "--is-ancestor", working_sha, "HEAD"],
            capture_output=True).returncode
        check("the working branch is an ancestor of the worktree HEAD", rc == 0,
              f"merge-base --is-ancestor exited {rc}")

        # The inverse, which is the actual 0c45d2f failure: a worktree based on
        # `working` must NOT have diverged `main` behind it. Without this, a
        # worktree wrongly based on main would still pass the check above
        # whenever main happened to be an ancestor.
        main_sha = git(root, "rev-parse", "main")
        rc_main = subprocess.run(
            ["git", "-C", path, "merge-base", "--is-ancestor", main_sha, "HEAD"],
            capture_output=True).returncode
        check("a diverged main is NOT an ancestor of it", rc_main != 0,
              "the worktree is on main, which is the 0c45d2f failure")

        # --- refusals ---------------------------------------------------------
        try:
            wt.create(root, "unit-b", "no-such-branch")
            check("an unresolvable base is refused", False, "it was accepted")
        except wt.WorktreeError as exc:
            check("an unresolvable base is refused", True)
            check("...and the reason names the base", "no-such-branch" in str(exc),
                  str(exc))

        try:
            wt.create(root, "unit-a", "working")
            check("a name already in use is refused", False, "it was accepted")
        except wt.WorktreeError as exc:
            check("a name already in use is refused", True)
            check("...and the reason names the name", "unit-a" in str(exc), str(exc))

        # A crafted name must not reach outside the repository. The containment
        # check is on the RESOLVED path, so `..` and an absolute name are the
        # same defect and are asserted as one.
        for evil in ("../escape", "a/../../escape", "/tmp/escape"):
            try:
                wt.create(root, evil, "working")
                check(f"a name escaping the root is refused: {evil}", False,
                      "it was accepted")
            except wt.WorktreeError:
                check(f"a name escaping the root is refused: {evil}", True)

        # --- remove is idempotent --------------------------------------------
        wt.remove(root, "unit-a")
        check("remove() takes the worktree away", not Path(path).exists(), path)
        wt.remove(root, "unit-a")
        check("remove() is idempotent", True)

        for evil in ("../escape", "/tmp/escape"):
            try:
                wt.remove(root, evil)
                check(f"remove refuses to escape the root: {evil}", False,
                      "it was accepted")
            except wt.WorktreeError:
                check(f"remove refuses to escape the root: {evil}", True)
    finally:
        # Guaranteed, because an in-place mutation without a restore left a
        # mutated file on disk earlier in this repository's history.
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} failed: {', '.join(failures)}")
        return 1
    print("All worktree tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
