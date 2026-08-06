"""pre-commit -- scans staged files for credentials before a commit is allowed.

The one hook here that can block. It returns a PreToolUse deny rather than a
non-zero exit code, because it is now registered with Claude Code directly and
that is the only signal the harness acts on.

Filtering is the script's own job: it is registered on PreToolUse for shell
tools, which covers every command, so it must confirm the command really is a
`git commit` -- and not a `--dry-run` -- before scanning anything.

Exit code is still set on a finding, so `run_hook.py` keeps working for any
caller that reads it.
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
    deny,
    is_git_commit,
    load_payload,
)

# SECRET_PATTERNS moved to _hooklib on 2026-08-02 so that
# post-run/06-artifact-autocommit.py enforces the identical rule. Its commits
# are made from a subprocess and never reach PreToolUse, so this hook cannot see
# them -- and a second copy of these patterns would eventually diverge from the
# one guarding the unattended path.

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


def main():
    payload = load_payload()
    command = command_of(payload)

    # Registered on every shell call, so confirm this is really a commit.
    # A payload with no command came from run_hook.py, which only invokes this
    # hook when a commit is genuinely happening -- so let that through.
    if command and (not is_git_commit(command) or DRY_RUN_RE.search(command)):
        return

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
        deny(
            "pre-commit secret scan flagged a likely credential in: "
            + ", ".join(findings)
            + ". Remove the secret and re-stage before committing."
        )
        # `deny()` emits the structured PreToolUse decision. Structured hook
        # output must return 0; exit 2 is reserved for stderr-only blocking.
        return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass
