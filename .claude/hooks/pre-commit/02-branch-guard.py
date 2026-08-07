"""pre-commit -- refuses a commit made directly onto a protected branch.

Sits alongside 01-secret-scan.py on the same event: both answer "is this commit
allowed", one on content, one on destination.

Decision policy: `deny`, not `ask`. An `ask` would be invisible here -- the
global review_gate already forces an ask on every unreviewed commit, so a second
one adds no signal at the moment it matters (a commit that HAS a review receipt
sails straight through to main, which is exactly the case worth catching).

Escape hatches, because "never commit to main" has real exceptions:
  - the very first commit (an unborn HEAD has no branch to switch off of)
  - ALLOW_MAIN_COMMIT=1 in the environment, for a deliberate one-off

Fails open: any error allows the commit. A guard that cannot read git state must
not be able to wedge the repo.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    command_of,
    deny,
    git_target_dir,
    is_git_commit,
    load_payload,
)

PROTECTED = {"main", "master", "develop", "release"}

# `is_git_commit` from _hooklib, not a regex. `-C` takes a value and no
# repetition can consume it, so the old pattern missed every
# `git -C <dir> commit` -- which is exactly the cross-repo case this hook now
# has to catch.
DRY_RUN_RE = re.compile(r"--dry-run\b")


def git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        timeout=15, shell=False,
    )


# A command can commit into a repository that is not the session's.
#   cd ../other && git commit …
#   git -C ../other commit …
# Until 2026-08-03 this hook resolved the branch from `payload["cwd"]` only, so
# it read the SESSION's branch and cheerfully allowed eight commits onto another
# repo's protected `main` -- silently, which is the worst way for a guard to
# fail. See ISSUES.md 2026-08-03 14:20.
#
# The resolver lives in `_hooklib` and is a tokeniser. This file carried its own
# regex until the second occurrence of the same bug: it assumed every git global
# flag is `-x value`, so `git --no-pager -C ../other commit` slipped past and the
# guard read the session's branch again. `03-attribution-guard.py` needs the same
# answer and had a third implementation that disagreed. One copy now.
target_dir = git_target_dir


def main():
    payload = load_payload()
    command = command_of(payload)

    # Registered on every shell call -- confirm this is really a commit.
    if not command or not is_git_commit(command) or DRY_RUN_RE.search(command):
        return

    if os.environ.get("ALLOW_MAIN_COMMIT") == "1":
        return

    # The command's target, not the session's directory. These differ whenever a
    # command reaches into a sibling repo, and that difference is what let eight
    # commits onto a protected branch.
    cwd = target_dir(command, payload.get("cwd") or os.getcwd())

    root = git(["rev-parse", "--show-toplevel"], cwd)
    if root.returncode != 0:
        return  # not a repo; nothing to protect

    # An unborn HEAD means no commits exist yet. The initial commit has to land
    # somewhere, and there is no branch to move off of, so allow it.
    if git(["rev-parse", "--verify", "HEAD"], cwd).returncode != 0:
        return

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd).stdout.strip()
    if branch not in PROTECTED:
        return

    # Name the repository whenever it is not the session's own. "you are on
    # 'main'" is baffling when the session is on a feature branch and the
    # command reaches into a sibling repo.
    session_root = git(["rev-parse", "--show-toplevel"],
                       payload.get("cwd") or os.getcwd()).stdout.strip()
    where = ""
    if session_root and session_root != root.stdout.strip():
        where = f" in {os.path.basename(root.stdout.strip())}"

    deny(
        f"branch-guard: the target repo{where} is on '{branch}', a protected "
        f"branch. Create a branch first:\n\n"
        f"    git checkout -b <short-descriptive-name>\n\n"
        f"then commit there. To override deliberately for one command, prefix "
        f"it with ALLOW_MAIN_COMMIT=1."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
