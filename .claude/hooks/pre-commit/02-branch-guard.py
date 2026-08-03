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
from _hooklib import command_of, deny, is_git_commit, load_payload  # noqa: E402

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
CD_RE = re.compile(r"(?:^|&&|;|\|\|)\s*cd\s+(?:--\s+)?([\"']?)([^\s\"'&;|]+)\1")
GIT_C_RE = re.compile(r"\bgit\s+(?:-\w+\s+\S+\s+)*-C\s+([\"']?)([^\s\"'&;|]+)\1")


def target_dir(command: str, session_cwd: str) -> str:
    """Where the command's git will actually run.

    `git -C` wins over `cd`: it is applied per-invocation and overrides whatever
    directory the shell is in. Relative paths resolve against the last `cd` if
    there was one, otherwise against the session cwd -- the same way the shell
    would do it.
    """
    def resolve(against: str, candidate: str) -> str:
        return candidate if os.path.isabs(candidate) else os.path.join(against, candidate)

    base = session_cwd

    # The LAST cd is the one in effect when git runs: `cd a && cd b && git …`
    # commits in b.
    cds = CD_RE.findall(command)
    if cds:
        base = resolve(base, cds[-1][1])

    git_cs = GIT_C_RE.findall(command)
    if git_cs:
        base = resolve(base, git_cs[-1][1])

    return base if os.path.isdir(base) else session_cwd


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
