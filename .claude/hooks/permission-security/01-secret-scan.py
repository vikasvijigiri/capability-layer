"""permission-security -- scans staged files for credentials before a commit is allowed.

The one check here that can block on content. It returns a PreToolUse deny
rather than a non-zero exit code, because it is registered with Claude Code
directly and that is the only signal the harness acts on.

Filtering is this check's own job: it is dispatched for every shell tool call,
which covers every command, so it must confirm the command really is a
`git commit` -- and not a `--dry-run` -- before scanning anything.

Moved from `pre-commit/01-secret-scan.py` on 2026-08-21, refactored from a
standalone script into a `check(payload) -> str | None` function so
`00-dispatch.py` can call it in-process, in the same interpreter as its three
siblings, instead of paying a separate Python cold start for each. Behavior
is unchanged -- same patterns, same filtering, same refusal text; only the
call shape moved.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    SECRET_PATTERNS,
    command_of,
    is_git_commit,
    load_payload,
)

# SECRET_PATTERNS moved to _hooklib on 2026-08-02 so that
# stop-finalization/06-artifact-autocommit.py enforces the identical rule. Its
# commits are made from a subprocess and never reach PreToolUse, so this check
# cannot see them -- and a second copy of these patterns would eventually
# diverge from the one guarding the unattended path.

# `is_git_commit` from _hooklib, not a regex: `-C` takes a value and no
# repetition can consume it, so the old pattern silently skipped the scan on
# every `git -C <dir> commit`.
DRY_RUN_RE = re.compile(r"--dry-run\b")


def staged_files(payload):
    files = payload.get("files")
    if isinstance(files, list) and files:
        return files
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        return [f for f in out.stdout.splitlines() if f]
    except Exception:
        return []


def check(payload: dict) -> str | None:
    """The deny reason if this commit carries a likely credential, else None."""
    command = command_of(payload)

    # Dispatched on every shell call, so confirm this is really a commit.
    # A payload with no command came from run_hook.py, which only invokes this
    # check when a commit is genuinely happening -- so let that through.
    if command and (not is_git_commit(command) or DRY_RUN_RE.search(command)):
        return None

    files = staged_files(payload)
    findings = []
    for path in files:
        if not os.path.isfile(path):
            continue
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if any(p.search(text) for p in SECRET_PATTERNS):
            findings.append(path)

    if findings:
        return (
            "pre-commit secret scan flagged a likely credential in: "
            + ", ".join(findings)
            + ". Remove the secret and re-stage before committing."
        )
    return None


if __name__ == "__main__":
    from _hooklib import deny  # noqa: E402
    try:
        reason = check(load_payload())
        if reason:
            deny(reason)
    except SystemExit:
        raise
    except Exception:
        pass
