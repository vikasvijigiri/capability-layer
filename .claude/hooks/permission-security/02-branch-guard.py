"""permission-security -- refuses a commit made directly onto a protected branch.

Sits alongside 01-secret-scan.py on the same event: both answer "is this
commit allowed", one on content, one on destination.

Decision policy: deny, not ask. An ask would be invisible here -- a commit
that has real review sails straight through anyway, so an ask adds no signal
at the moment it matters.

Escape hatches, because "never commit to main" has real exceptions:
  - the very first commit (an unborn HEAD has no branch to switch off of)
  - ALLOW_MAIN_COMMIT=1 in the environment, for a deliberate one-off

Fails open: any error allows the commit. A guard that cannot read git state
must not be able to wedge the repo.

Moved from `pre-commit/02-branch-guard.py` on 2026-08-21, refactored into a
`check(payload) -> str | None` function so `00-dispatch.py` can call it
in-process alongside its three siblings. Behavior unchanged.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    command_of,
    git_target_dir,
    is_git_commit,
    load_payload,
)

PROTECTED = {"main", "master", "develop", "release"}

DRY_RUN_RE = re.compile(r"--dry-run\b")


def git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        timeout=15, shell=False,
    )


# A command can commit into a repository that is not the session's:
#   cd ../other && git commit …
#   git -C ../other commit …
# The resolver lives in `_hooklib` and is a tokeniser, shared with
# 03-attribution-guard.py so the two agree on which repo a command targets.
target_dir = git_target_dir


def check(payload: dict) -> str | None:
    """The deny reason if this commit targets a protected branch, else None."""
    command = command_of(payload)

    # Dispatched on every shell call -- confirm this is really a commit.
    if not command or not is_git_commit(command) or DRY_RUN_RE.search(command):
        return None

    if os.environ.get("ALLOW_MAIN_COMMIT") == "1":
        return None

    # The command's target, not the session's directory. These differ
    # whenever a command reaches into a sibling repo.
    cwd = target_dir(command, payload.get("cwd") or os.getcwd())

    root = git(["rev-parse", "--show-toplevel"], cwd)
    if root.returncode != 0:
        return None  # not a repo; nothing to protect

    # An unborn HEAD means no commits exist yet -- allow the initial commit.
    if git(["rev-parse", "--verify", "HEAD"], cwd).returncode != 0:
        return None

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).stdout.strip()
    if branch not in PROTECTED:
        return None

    # Name the repository whenever it is not the session's own.
    session_root = git(["rev-parse", "--show-toplevel"],
                       payload.get("cwd") or os.getcwd()).stdout.strip()
    where = ""
    if session_root and session_root != root.stdout.strip():
        where = f" in {os.path.basename(root.stdout.strip())}"

    return (
        f"branch-guard: the target repo{where} is on '{branch}', a protected "
        f"branch. Create a branch first:\n\n"
        f"    git checkout -b <short-descriptive-name>\n\n"
        f"then commit there. To override deliberately for one command, prefix "
        f"it with ALLOW_MAIN_COMMIT=1."
    )


if __name__ == "__main__":
    from _hooklib import deny  # noqa: E402
    try:
        reason = check(load_payload())
        if reason:
            deny(reason)
    except Exception:
        pass
