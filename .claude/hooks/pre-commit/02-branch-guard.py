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
from _hooklib import command_of, deny, load_payload  # noqa: E402

PROTECTED = {"main", "master", "develop", "release"}

COMMIT_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b")
DRY_RUN_RE = re.compile(r"--dry-run\b")


def git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        timeout=15, shell=False,
    )


def main():
    payload = load_payload()
    command = command_of(payload)

    # Registered on every shell call -- confirm this is really a commit.
    if not command or not COMMIT_RE.search(command) or DRY_RUN_RE.search(command):
        return

    if os.environ.get("ALLOW_MAIN_COMMIT") == "1":
        return

    cwd = payload.get("cwd") or os.getcwd()

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

    deny(
        f"branch-guard: you are on '{branch}', a protected branch. Create a "
        f"branch first:\n\n    git checkout -b <short-descriptive-name>\n\n"
        f"then commit there. To override deliberately for one command, prefix "
        f"it with ALLOW_MAIN_COMMIT=1."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
