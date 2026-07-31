"""pre-commit -- refuses a substantial commit that records nothing in LOG.md.

Why this exists alongside the other two docs hooks
--------------------------------------------------
Three hooks now watch the same concern at three different moments, because each
catches something the others cannot:

- `pre-run/04-docs-staleness.py` (UserPromptSubmit) warns at the start of a turn.
  Cheap, informative, easy to act on. Cannot compel anything.
- `post-run/05-docs-gate.py` (Stop) blocks the turn from ending. Catches work
  that sits uncommitted for hours and might never reach a commit at all.
  Its `decision: block` mechanism is, as of 2026-07-31, unproven in this build --
  130 Stop payloads have been delivered and not one Stop hook has ever blocked.
- This hook (PreToolUse) blocks the commit itself. `PreToolUse` deny is the one
  mechanism here that is demonstrably real: `01-secret-scan.py`,
  `02-branch-guard.py` and `04-delivery-guard.py` each blocked a commit on
  2026-07-31.

The harm being prevented is unrecorded *history*. Once a commit lands, the
staleness is baked in and `git status` goes clean, so every other signal
disappears. This is the last moment it is still visible.

Scope
-----
Only `git commit`, only above MIN_FILES staged, and only when the staged set
includes neither LOG.md nor HANDOFF.md. A gate that fires on a two-file fix
would be noise, and noise is how a gate stops being read.

`ALLOW_UNLOGGED_COMMIT=1` overrides deliberately, for the commit genuinely not
worth a log entry. An override that must be typed is a decision; a gate with no
override is something people learn to route around.
"""

import os

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import command_of, deny, load_payload, write_log  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

DOCS = ("LOG.md", "HANDOFF.md")
MIN_FILES = 10

# Global git options that consume the following token, so `git -C /repo commit`
# is recognised. A regex was tried first and got this wrong in both directions:
# it missed `git -C /repo commit` (the value is a separate token) and matched
# `git commit-tree` (`\b` matches before a hyphen). Tokenising is clearer than
# the regex that would be needed to handle both.
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def is_git_commit(command: str) -> bool:
    """True for a real `git commit` invocation, false for lookalikes."""
    toks = command.split()
    for i, tok in enumerate(toks):
        if tok != "git" and not tok.endswith("/git"):
            continue
        j = i + 1
        while j < len(toks) and toks[j].startswith("-"):
            if toks[j] in VALUE_FLAGS:
                j += 1  # skip its value too
            j += 1
        if j < len(toks) and toks[j] == "commit":
            return True
    return False


def staged_files():
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [l.strip() for l in proc.stdout.splitlines() if l.strip()]


def main():
    payload = load_payload()
    command = command_of(payload) or ""
    if not is_git_commit(command):
        return
    if os.environ.get("ALLOW_UNLOGGED_COMMIT") == "1":
        write_log("pre-commit-scan.log", "DOCS-REQUIRED-OVERRIDE", {"command": command[:120]})
        return

    staged = staged_files()
    if staged is None:
        return  # git could not answer -- never block on a broken check

    work = [f for f in staged if f not in DOCS]
    if len(work) < MIN_FILES:
        return
    if any(d in staged for d in DOCS):
        return

    write_log("pre-commit-scan.log", "DOCS-REQUIRED-DENY", {"staged": len(work)})
    deny(
        f"{len(work)} files staged and neither LOG.md nor HANDOFF.md is among them. "
        "Invoke `knowledge-manager` to record this unit of work, then stage the docs "
        "and commit again. Once this commit lands, `git status` goes clean and the "
        "staleness is invisible -- this is the last point it can be caught. "
        "Set ALLOW_UNLOGGED_COMMIT=1 for a commit genuinely not worth logging."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
