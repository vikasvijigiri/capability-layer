#!/usr/bin/env python3
"""`git_ops` proved against real temp repos, not mocked git.

Same argument `tools/test_worktree.py` makes for itself: the property under
test lives in git's own resolution of refs and merges, and a fake `git` would
only prove the fake agrees with itself. Every repo here is a real `git init`
in a temp directory, torn down in a `finally`.

Run: python tools/test_git_ops.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_ops  # noqa: E402

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


def write(root: Path, name: str, text: str) -> None:
    (root / name).write_text(text, encoding="utf-8")


def init_repo(root: Path) -> None:
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "config", "core.autocrlf", "false")


def conflicting_repo(root: Path) -> None:
    """`main` and `working` both edit `app.py`'s same line -- a real,
    reproducible content conflict, plus an untouched `package-lock.json` on
    `working` so the mechanical case has a genuine second file to point at."""
    init_repo(root)
    write(root, "app.py", "value = 1\n")
    write(root, "package-lock.json", '{"lockfileVersion": 1}\n')
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")

    git(root, "checkout", "-q", "-b", "working")
    write(root, "app.py", "value = 2  # working\n")
    write(root, "package-lock.json", '{"lockfileVersion": 2}\n')
    git(root, "add", "-A")
    git(root, "commit", "-qm", "wip: change app and lockfile")

    git(root, "checkout", "-q", "main")
    write(root, "app.py", "value = 3  # main\n")
    write(root, "package-lock.json", '{"lockfileVersion": 3}\n')
    git(root, "add", "-A")
    git(root, "commit", "-qm", "wip: main moved on")
    git(root, "checkout", "-q", "working")


def clean_repo(root: Path) -> None:
    """`working` adds a new file that never collides with `main`."""
    init_repo(root)
    write(root, "base.txt", "base\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")

    git(root, "checkout", "-q", "-b", "working")
    write(root, "new.txt", "new\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "wip: add new file")

    git(root, "checkout", "-q", "main")
    write(root, "other.txt", "other\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "wip: main moved too")
    git(root, "checkout", "-q", "working")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="gitops-test-"))
    try:
        # === rebase_plan =====================================================
        conflict_root = tmp / "conflict-repo"
        conflict_root.mkdir()
        conflicting_repo(conflict_root)

        result = git_ops.rebase_plan(conflict_root, "main", "working")
        check("rebase_plan reports 'conflict' for a real two-branch conflict",
              result["would"] == "conflict", str(result))
        check("...and names the conflicting file", "app.py" in result["conflicts"],
              str(result))
        check("...and never touched the index",
              git(conflict_root, "status", "--porcelain") == "",
              "the working tree changed as a side effect of reporting")
        check("...and never created a rebase in progress",
              not (conflict_root / ".git" / "rebase-merge").exists()
              and not (conflict_root / ".git" / "rebase-apply").exists(),
              "a rebase was actually started")

        clean_root = tmp / "clean-repo"
        clean_root.mkdir()
        clean_repo(clean_root)
        clean_result = git_ops.rebase_plan(clean_root, "main", "working")
        check("rebase_plan reports 'clean' when nothing collides",
              clean_result["would"] == "clean", str(clean_result))
        check("...and lists the commit that would replay",
              any("add new file" in c for c in clean_result["commits"]),
              str(clean_result))

        noop = git_ops.rebase_plan(clean_root, "working", "working")
        check("rebase_plan reports 'no-op' for base == head",
              noop["would"] == "no-op", str(noop))

        unresolvable = git_ops.rebase_plan(clean_root, "no-such-branch", "working")
        check("rebase_plan reports 'unknown' for an unresolvable base",
              unresolvable["would"] == "unknown", str(unresolvable))

        offline = git_ops.rebase_plan(clean_root, "main", "working", offline=True)
        check("rebase_plan --offline reports 'unknown' rather than inventing a fact",
              offline["would"] == "unknown", str(offline))

        # === classify_conflict, both directions ==============================
        substantive = git_ops.classify_conflict(["app.py"])
        check("classify_conflict: a plain source file is substantive",
              substantive["class"] == "substantive" and substantive["escalate"],
              str(substantive))

        mechanical = git_ops.classify_conflict(["package-lock.json"])
        check("classify_conflict: a lockfile is mechanical",
              mechanical["class"] == "mechanical" and not mechanical["escalate"],
              str(mechanical))

        # The SAME conflict, classified both ways at once -- the plan asks for
        # exactly this: one conflict, two files, one mechanical and one not.
        both = git_ops.classify_conflict(["app.py", "package-lock.json"])
        check("classify_conflict: mixed conflict escalates as a whole",
              both["class"] == "substantive" and "app.py" in both["matched"],
              str(both))

        migration = git_ops.classify_conflict(["db/migrate/001_add_users.rb"])
        check("classify_conflict: a migration path is substantive",
              migration["class"] == "substantive", str(migration))

        auth = git_ops.classify_conflict(["src/auth/session.py"])
        check("classify_conflict: an auth path is substantive",
              auth["class"] == "substantive", str(auth))

        unknown_paths = git_ops.classify_conflict([])
        check("classify_conflict: no paths is 'unknown', not mechanical",
              unknown_paths["class"] == "unknown", str(unknown_paths))

        # === pr_body ==========================================================
        plan_text = (
            "# A Plan\n\n"
            "**Goal:** ship the thing that matters, stated once.\n\n"
            "**Risk:** high\n\n"
            "## Progress\n\n"
            "- [x] Task 1 — do the first thing\n"
            "- [ ] Task 2 — not done yet\n"
            "- [x] Task 3 — do the third thing\n"
        )
        body = git_ops.pr_body(plan_text, tier="high",
                               findings=[{"severity": "advisory",
                                          "code": "stack-depth",
                                          "finding": "2 PRs deep"}])
        check("pr_body includes the plan's Goal",
              "ship the thing that matters" in body, body)
        check("pr_body includes a ticked task", "do the first thing" in body, body)
        check("pr_body excludes an unticked task",
              "not done yet" not in body, body)
        # `_PROGRESS_RE`'s box/task-number prefix is `_hooklib.PROGRESS_BOX_PATTERN`
        # (imported as text, then extended with this module's own title
        # suffix) rather than a fourth private retyping.
        check("_PROGRESS_RE's prefix is the shared PROGRESS_BOX_PATTERN text",
              git_ops._PROGRESS_RE.pattern.startswith(
                  git_ops._hooklib_gitops.PROGRESS_BOX_PATTERN))
        check("pr_body includes the risk tier", "high" in body, body)
        check("pr_body includes the review finding",
              "stack-depth" in body and "2 PRs deep" in body, body)

        commit_only_body = git_ops.pr_body(plan_text)
        raw_commits = git(conflict_root, "log", "--format=%s").splitlines()
        check("pr_body never contains a raw wip: commit subject",
              not any(c in commit_only_body for c in raw_commits if c),
              f"a commit subject leaked into the composed body: {raw_commits}")

        no_goal_body = git_ops.pr_body("no goal line here")
        check("pr_body names a missing Goal rather than fabricating one",
              "no `**Goal:**` line found" in no_goal_body, no_goal_body)

        # === it never acquires the one forbidden verb ========================
        import re
        src = Path(__file__).resolve().parent.joinpath("git_ops.py") \
            .read_text(encoding="utf-8")
        merge_hits = [ln for ln in src.splitlines()
                      if re.search(r"(?<![`\w])gh pr merge(?![\w])", ln)
                      and not re.search(r"\b(never|not|no|nor)\b", ln, re.I)]
        check("git_ops.py never acquires 'gh pr merge' unnegated",
              not merge_hits, str(merge_hits))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} failed: {', '.join(failures)}")
        return 1
    print("All git_ops tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
