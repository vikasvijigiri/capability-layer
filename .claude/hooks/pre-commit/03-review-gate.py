"""Review Gate -- PreToolUse hook for `git commit` / `git push`.

Skills cannot fire themselves: nothing in the harness invokes `code-review`, so whether
it runs is a judgment call, and judgment is exactly what gets skipped under time pressure.
This hook converts that judgment into a mechanism. A commit is held for explicit approval
unless a review receipt exists whose fingerprint matches the change being committed.

Two modes:

  stdin (hook)   PreToolUse payload -> allow silently, or return "ask" with the reason.
  --record       Writes the receipt for the current change. The `code-review` skill runs
                 this as its final step, so the receipt can only exist if a review did.

The fingerprint is the content of the change itself, not a timestamp. Amending the diff
after a review invalidates the receipt automatically -- reviewing one change and
committing a different one is the failure this is built to catch.

Fails open by design: any internal error allows the operation. A broken gate must never
be able to wedge a session.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402


import hashlib
import json
import os
import re
import subprocess
import sys
import time

# Receipts live beside the hooks, inside this repo. Previously this resolved to
# ~/.claude/state/, which meant one shared receipt store for every repo on the
# machine -- a review recorded in project A could satisfy a commit in project B
# if the diffs happened to fingerprint alike. Repo-local is the correct scope.
STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "review-receipts.json")

# Only real delivery actions are gated. `git commit --dry-run`, `git log`, `git status`
# and friends must stay frictionless.
COMMIT_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b")
PUSH_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*push\b")
DRY_RUN_RE = re.compile(r"--dry-run\b")

# A receipt older than this is treated as stale even if the diff still matches, so a
# review from days ago cannot silently authorise today's commit.
MAX_RECEIPT_AGE_SECONDS = 6 * 60 * 60


def run_git(args: list[str], cwd: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def repo_root(cwd: str) -> str | None:
    root = run_git(["rev-parse", "--show-toplevel"], cwd).strip()
    return root or None


def fingerprint(root: str, action: str) -> str | None:
    """Content hash of what is about to be delivered, or None when there is nothing.

    `--porcelain` is included alongside the diffs because diffs alone see only tracked
    content. A first commit, or any change made entirely of new files, produces empty
    `diff --cached` and `diff HEAD` output -- so relying on diffs would let exactly the
    commits most in need of review through unnoticed.

    Known limit: for an untracked file the porcelain line carries its path but not its
    content, so editing an untracked file does not invalidate a receipt. Adding or
    removing one does.
    """
    if action == "push":
        head = run_git(["rev-parse", "HEAD"], root).strip()
        # No commits means nothing to push; git will refuse on its own.
        return hashlib.sha256(head.encode("utf-8")).hexdigest() if head else None

    blob = "\n".join((
        run_git(["status", "--porcelain"], root),
        run_git(["diff", "--cached"], root),
        run_git(["diff"], root),
    ))
    if not blob.strip():
        return None
    return hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()


def load_receipts() -> dict:
    try:
        with open(os.path.abspath(STATE_PATH), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_receipt(root: str, digest: str, action: str) -> None:
    path = os.path.abspath(STATE_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    receipts = load_receipts()
    receipts[root.lower()] = {"digest": digest, "action": action, "at": time.time()}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(receipts, handle)


def ask(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))


def record() -> int:
    cwd = os.getcwd()
    root = repo_root(cwd)
    if root is None:
        print("Not a git repository -- nothing to record.")
        return 1
    digest = fingerprint(root, "commit")
    if digest is None:
        print("No staged or unstaged changes -- nothing to review.")
        return 1
    save_receipt(root, digest, "commit")
    print(f"Review receipt recorded for {root} ({digest[:12]}).")
    return 0


def main() -> None:
    if "--record" in sys.argv:
        sys.exit(record())

    try:
        data = _load_payload()
    except (json.JSONDecodeError, ValueError):
        return

    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return

    command = (data.get("tool_input") or {}).get("command") or ""
    if DRY_RUN_RE.search(command):
        return

    if COMMIT_RE.search(command):
        action = "commit"
    elif PUSH_RE.search(command):
        action = "push"
    else:
        return

    cwd = data.get("cwd") or os.getcwd()
    root = repo_root(cwd)
    if root is None:
        return

    digest = fingerprint(root, action)
    if digest is None:
        return

    receipt = load_receipts().get(root.lower())

    if receipt is None:
        ask(
            f"No code review has been recorded for this {action}.\n\n"
            "CLAUDE.md lists diff review as a mandatory gate. Run the `code-review` "
            "skill on this diff, then record it with:\n"
            f'    python "{os.path.abspath(__file__)}" --record\n\n'
            "Approve only if you deliberately want to skip review."
        )
        return

    if receipt.get("digest") != digest:
        ask(
            f"The change has been modified since it was reviewed, so the existing "
            f"review no longer covers this {action}.\n\n"
            "Re-run `code-review` on the current diff and record it again. "
            "Approve only if you accept committing unreviewed changes."
        )
        return

    age = time.time() - float(receipt.get("at", 0))
    if age > MAX_RECEIPT_AGE_SECONDS:
        ask(
            f"The review for this change is {int(age // 3600)} hours old and has expired.\n\n"
            "Re-run `code-review` to confirm it still holds, then record it again."
        )
        return

    # Reviewed, unchanged and recent -- allow silently.


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - fail open; a hook must never wedge a session
        pass
