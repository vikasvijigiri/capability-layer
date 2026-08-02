"""Review Gate -- PreToolUse hook for `git commit`, `git push` and `gh pr create`.

Whether the diff gets reviewed is a judgment call, and judgment is exactly what gets
skipped under time pressure. This hook converts that judgment into a mechanism. A
delivery action is held for explicit approval unless a review receipt exists whose
fingerprint matches the change being delivered.

Two modes:

  stdin (hook)   PreToolUse payload -> allow silently, or return "ask" with the reason.
  --record       Writes the receipt for the current change. Run this as the last step of
                 a review, so the receipt can only exist if a review actually happened.
                 Add `--pr` to record a pull-request review instead of a commit one.

The `code-review` skill owns both the review and the `--record` call. It requires the
user's sign-off before recording, so the receipt cannot exist without a human having
been asked. Nothing else should call `--record`.

The fingerprint is the content of the change itself, not a timestamp. Amending the diff
after a review invalidates the receipt automatically -- reviewing one change and
committing a different one is the failure this is built to catch.

A pull request delivers more than the working tree: it delivers every commit on this
branch that the base does not have. So the PR fingerprint covers the branch diff as
well as the working tree, which also means a commit review does not silently satisfy a
PR gate. Reviewing today's edit is not reviewing the twelve commits shipping with it.

Fails open by design: any internal error allows the operation. A broken gate must never
be able to wedge a session.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    authorization_in as _authorization_in,
    find_transcript as _find_transcript,
    load_payload as _load_payload,
    recent_user_messages as _recent_user_messages,
)

# Phrases that mean the user signed off on a review, in their own words or via an
# AskUserQuestion click. Scanned over a SHORT window -- sign-off has to be about
# the change in front of us, not something said twenty turns ago about a diff
# that has since moved.
SIGNOFF_PATTERNS = [
    r"\bapprove(?:d)?\b",
    r"\bsign(?:ed)?[-\s]?off\b",
    r"\blgtm\b",
    r"\blooks good\b",
    r"\brecord it\b",
    r"\bship it\b",
    r"\bgo ahead\b",
    r"\byes\b",
]
# One turn, not several. `recent_user_messages` already filters to real user
# text plus AskUserQuestion clicks, so "the last user turn" means the last thing
# the user actually said or chose. A four-turn window matched an "Approve" click
# from six turns earlier that had approved a task brief, not this diff -- close
# enough to look right, wrong enough to record a receipt nobody gave.
#
# This still cannot prove WHAT was approved, only that approval was the user's
# most recent act. That is a speed bump, not a proof; the skill's HARD-GATE
# remains the real control, and this stops the accidental case that already
# happened once.
SIGNOFF_LOOKBACK = 1

# The approval word must land in the first few words. "Approve and record" and
# "yes, go ahead" lead with the decision; "I review, you approve" -- an option
# label about who reviews -- does not, and matched before this was added.
SIGNOFF_HEAD_WORDS = 3


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

# The receipts file is tracked, so writing a receipt changes `git status --porcelain`
# and `git diff` -- which changes the very fingerprint the receipt was just recorded
# under. Every receipt invalidated itself the instant it was written, and the gate
# asked forever; the 2026-08-01 receipt reported "the change has been modified since
# it was reviewed" for exactly this reason and nothing else. Excluding the path from
# every fingerprint input is the fix. Gitignoring the file would also work, but it is
# already tracked and this holds either way.
RECEIPTS_PATHSPEC = ":(exclude).claude/hooks/state/review-receipts.json"

# Only real delivery actions are gated. `git commit --dry-run`, `git log`, `git status`
# and friends must stay frictionless.
COMMIT_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*commit\b")
PUSH_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*push\b")
DRY_RUN_RE = re.compile(r"--dry-run\b")

# Only PR verbs that actually deliver. `gh pr view`, `list`, `diff`, `checks` and
# `status` are read-only and must stay frictionless -- gating them would make the
# gate itself the reason people stop inspecting PRs.
PR_RE = re.compile(r"\bgh\s+pr\s+(?:create|merge|ready)\b")

# Bases tried in order when working out what a PR would actually deliver.
PR_BASES = ("origin/main", "origin/master", "main", "master")

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

    parts = [
        run_git(["status", "--porcelain", "--", ".", RECEIPTS_PATHSPEC], root),
        run_git(["diff", "--cached", "--", ".", RECEIPTS_PATHSPEC], root),
        run_git(["diff", "--", ".", RECEIPTS_PATHSPEC], root),
    ]
    if action == "pull request":
        parts.append(branch_diff(root))

    blob = "\n".join(parts)
    if not blob.strip():
        return None
    return hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()


def branch_diff(root: str) -> str:
    """Everything this branch would deliver that the base does not already have.

    Falls back to the HEAD sha when no base can be resolved -- a detached head, a
    repo with no `main`/`master`, or no remote. That still fingerprints *something*
    that changes per commit, so the gate keeps asking rather than going quiet, which
    is the safe direction for a hook that fails open everywhere else.
    """
    for base in PR_BASES:
        merge_base = run_git(["merge-base", "HEAD", base], root).strip()
        if merge_base:
            return run_git(
                ["diff", merge_base, "HEAD", "--", ".", RECEIPTS_PATHSPEC], root)
    return run_git(["rev-parse", "HEAD"], root)


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


def signoff_evidence(cwd: str):
    """The user's own sign-off words from the last few turns, or None.

    A receipt asserts that a human saw this change and accepted it. Nothing used
    to check that: on 2026-08-01 a `--record` run made purely to test the
    mechanism wrote a receipt claiming a sign-off that had never happened, and it
    was undetectable afterwards because a forged receipt and a real one are the
    same file. `--record` has no way to know whether its caller is a review or a
    test, so the evidence has to come from outside it -- the transcript.

    Fails CLOSED, unlike every other path in this hook: no transcript, no
    messages, or no matching phrase all mean "cannot prove a sign-off", and
    refusing to record merely leaves the gate asking. A gate that asks when it
    should not is recoverable; a forged receipt silently disarms it.
    """
    messages = _recent_user_messages(_find_transcript(cwd))
    return _authorization_in(messages, SIGNOFF_PATTERNS,
                             max_turns=SIGNOFF_LOOKBACK,
                             head_words=SIGNOFF_HEAD_WORDS)


def record(action: str = "commit", force: bool = False) -> int:
    cwd = os.getcwd()
    root = repo_root(cwd)
    if root is None:
        print("Not a git repository -- nothing to record.")
        return 1

    if not force:
        evidence = signoff_evidence(cwd)
        if evidence is None:
            print(
                "Refusing to record: no user sign-off found in the last "
                f"{SIGNOFF_LOOKBACK} turns.\n"
                "A receipt claims a human reviewed this change. Present the "
                "findings and get an explicit answer first.\n"
                "Use --force only to test the mechanism itself, never to record "
                "a real review."
            )
            return 2
        print(f"Sign-off found: {evidence!r}")
    digest = fingerprint(root, action)
    if digest is None:
        print("Nothing to review -- no changes and nothing ahead of the base.")
        return 1
    save_receipt(root, digest, action)
    print(f"Review receipt recorded for {root} [{action}] ({digest[:12]}).")
    return 0


def main() -> None:
    if "--record" in sys.argv:
        sys.exit(record(
            "pull request" if "--pr" in sys.argv else "commit",
            force="--force" in sys.argv,
        ))

    try:
        data = _load_payload()
    except (json.JSONDecodeError, ValueError):
        return

    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return

    command = (data.get("tool_input") or {}).get("command") or ""
    if DRY_RUN_RE.search(command):
        return

    if PR_RE.search(command):
        action = "pull request"
    elif COMMIT_RE.search(command):
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

    record_cmd = f'python "{os.path.abspath(__file__)}" --record'
    if action == "pull request":
        record_cmd += " --pr"

    if receipt is None:
        ask(
            f"No code review has been recorded for this {action}.\n\n"
            "CLAUDE.md lists diff review as a mandatory gate. Invoke the "
            "`code-review` skill, which reviews the change and asks you to sign "
            "off before it records:\n"
            f"    {record_cmd}\n\n"
            "Approve only if you deliberately want to skip review."
        )
        return

    # A commit review does not cover a PR. The digests usually differ on their own
    # because the PR fingerprint folds in the branch diff, but they collapse to the
    # same value when the branch is level with its base -- so check the kind too.
    if action == "pull request" and receipt.get("action") != "pull request":
        ask(
            "The recorded review covers the working tree, not this pull request.\n\n"
            "A PR delivers every commit this branch has that the base does not. "
            "Review the branch, then record it with:\n"
            f"    {record_cmd}\n\n"
            "Approve only if you accept opening an unreviewed pull request."
        )
        return

    if receipt.get("digest") != digest:
        ask(
            f"The change has been modified since it was reviewed, so the existing "
            f"review no longer covers this {action}.\n\n"
            "Re-review the current diff and record it again. "
            "Approve only if you accept committing unreviewed changes."
        )
        return

    age = time.time() - float(receipt.get("at", 0))
    if age > MAX_RECEIPT_AGE_SECONDS:
        ask(
            f"The review for this change is {int(age // 3600)} hours old and has expired.\n\n"
            "Re-review to confirm it still holds, then record it again."
        )
        return

    # Reviewed, unchanged and recent -- allow silently.


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 - fail open; a hook must never wedge a session
        pass
