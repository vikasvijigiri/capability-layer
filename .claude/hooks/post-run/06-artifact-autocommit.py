"""post-run -- commits this turn's work automatically, as a small local checkpoint.

Authorised by the user on 2026-08-02, widened from prose-only to all changed
files on the same day after the trade below was stated explicitly. Do not widen
it further -- to pushing, to protected branches -- without asking again.

Why this exists
---------------
This repo accumulated 91 uncommitted files across five sessions while 28 hooks
fired correctly, because every gate asked the model to act instead of acting.
The fix is not a bigger gate; it is a commit boundary that arrives on its own.

`pre-commit/03-review-gate.py` was the opposite approach -- ask a human on every
commit -- and it deadlocked and was deleted. Its replacement is this: commits are
cheap local checkpoints that nobody reviews, and **the review moves to the push
or the PR**, which is the boundary the user actually cares about. A commit that
needs a human is not a small commit; it is an expensive one, and expensive
commits are why the backlog grew.

What gates a checkpoint
-----------------------
Artefact facts, never process compliance -- the principle five comparable repos
converge on (stripe, rstudio, crowd.dev, claudekit, superpowers: every hook in
all of them verifies an artefact; not one enforces process).

  1. Something changed.
  2. The branch is not protected.
  3. No changed file matches a credential pattern.
  4. The repo's own suites pass.
  5. The change is small enough to still be a checkpoint.

Every clause is falsifiable. A failure refuses the commit and says so; nothing
is ever committed silently on a red suite.

Deliberately bypassed gates, and how that is covered
----------------------------------------------------
A commit made from this subprocess does not pass through `PreToolUse`, so
`01-secret-scan.py`, `02-branch-guard.py` and `01-forbidden-change-guard.py`
never see it. When the scope was prose that was tolerable. It is not tolerable
for code, so the two load-bearing checks are enforced *inline* here, from the
same `_hooklib` definitions those hooks use -- one rule, two enforcement points,
no second copy to drift.

Never pushes. Never `git add .`; always an explicit pathspec, so it cannot sweep
files somebody else staged. Never raises, never blocks the turn.

Message shape
-------------
`wip:` prefixed, deliberately. These are checkpoints, not curated history: the
hook can count files but cannot know why they changed. Squash-merging the branch
at PR time collapses them into the one message a human writes, so the noise has
a defined end. A checkpoint that pretended to be a real commit message would be
worse -- it would look reviewed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    AI_ATTRIBUTION_PATTERNS,
    PROTECTED_BRANCHES,
    changed_paths,
    current_branch,
    load_payload,
    scan_for_secrets,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Above this, the turn stopped being a checkpoint and became a unit of work
# somebody should look at before it is written down as one commit. Refusing is
# the safe direction: the files stay in the working tree and `03-checkpoint.py`
# has already snapshotted them, so nothing is at risk either way.
MAX_FILES = 25

# Paths never committed automatically, whatever else is true. `settings.json`
# decides what fires; committing a change to it unattended means the mechanism
# that governs this hook was altered without anyone reading the diff.
NEVER_AUTO = (".claude/settings.json", ".claude/settings.local.json")

SUITE_GLOB = "test_*.py"
SUITE_DIR = REPO_ROOT / "tools"

# Re-entry guard. `tools/test_hooks.py` fires the whole `post-run` event, which
# reaches this hook, which runs the suites, which runs `test_hooks.py` -- an
# unbounded recursion that presents as a hang, not an error. Found on 2026-08-02
# by the run timing out at two minutes.
#
# It does double duty: a suite run must never produce a real commit either, and
# any invocation carrying this flag is by definition running underneath one.
REENTRY_FLAG = "UAIOS_AUTOCOMMIT_RUNNING"


def git(*args):
    """Run git and return (rc, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001 -- reported below, never swallowed
        return 1, "", str(exc)


def speak(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": text,
    }}))


def run_suites():
    """(ok, detail). ok is False only when a suite actually ran and failed.

    A repo with no suites is not a failing repo -- it commits, and the caller
    says so, because "verified" and "nothing to verify" must not read alike.
    """
    if not SUITE_DIR.is_dir():
        return True, "no tools/ directory -- nothing to verify"
    suites = sorted(SUITE_DIR.glob(SUITE_GLOB))
    if not suites:
        return True, "no test suites found -- nothing to verify"

    failed = []
    for suite in suites:
        try:
            proc = subprocess.run(
                [sys.executable, str(suite)], cwd=str(REPO_ROOT),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=300,
                env={**os.environ, "PYTHONIOENCODING": "utf-8",
                     REENTRY_FLAG: "1"},
            )
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{suite.name} ({exc})")
            continue
        if proc.returncode != 0:
            tail = (proc.stdout or proc.stderr or "").strip().splitlines()
            failed.append(f"{suite.name}: {tail[-1] if tail else 'exit ' + str(proc.returncode)}")
    if failed:
        return False, "; ".join(failed)
    return True, f"{len(suites)} suite(s) green"


def build_message(paths, suite_detail):
    """A checkpoint subject the hook can actually justify, plus the evidence."""
    groups = {}
    for p in paths:
        head = p.split("/")[0] if "/" in p else "(root)"
        groups[head] = groups.get(head, 0) + 1
    summary = ", ".join(f"{k} ({v})" for k, v in sorted(groups.items()))
    subject = f"wip: checkpoint {len(paths)} file(s) -- {summary}"
    if len(subject) > 72:
        subject = f"wip: checkpoint {len(paths)} file(s) across {len(groups)} area(s)"

    listing = "\n".join(f"- {p}" for p in paths)
    return (
        f"{subject}\n\n"
        f"Automatic checkpoint from post-run/06-artifact-autocommit.py. Not a\n"
        f"reviewed commit: squashed at PR time, when a human reads the branch.\n\n"
        f"Verified before committing: {suite_detail}; no credential pattern in\n"
        f"the changed files; branch is not protected.\n\n"
        f"{listing}\n"
    )


def main():
    # Running underneath our own suite run: never recurse, never commit.
    if os.environ.get(REENTRY_FLAG):
        return

    payload = load_payload()
    if payload.get("stop_hook_active"):
        return

    paths = changed_paths(REPO_ROOT)
    if not paths:
        return

    paths = sorted(p for p in paths if p not in NEVER_AUTO)
    if not paths:
        return

    # --- gate 1: the branch
    branch = current_branch(REPO_ROOT)
    if branch is None:
        speak("Auto-commit skipped: could not read the current branch, so it "
              "cannot rule out a protected one. Commit by hand.")
        return
    if branch in PROTECTED_BRANCHES:
        speak(f"Auto-commit skipped: `{branch}` is a protected branch. Branch "
              f"first, then the checkpoint resumes on its own.")
        return

    # --- gate 2: size
    if len(paths) > MAX_FILES:
        speak(f"Auto-commit skipped: {len(paths)} changed files is past "
              f"MAX_FILES={MAX_FILES} and is a unit of work, not a checkpoint. "
              f"Review it and commit deliberately.")
        return

    # --- gate 3: secrets. This hook's commits never reach 01-secret-scan.py,
    # so the identical rule is enforced here from the same _hooklib patterns.
    findings = scan_for_secrets(paths, REPO_ROOT)
    if findings:
        speak("Auto-commit REFUSED: a credential pattern matched in "
              f"{', '.join(findings)}. Nothing was committed. Remove the secret "
              f"-- do not override; a committed key is unrecoverable once pushed.")
        return

    # --- gate 4: the suites
    ok, suite_detail = run_suites()
    if not ok:
        speak(f"Auto-commit skipped: suites are red ({suite_detail}). "
              f"{len(paths)} file(s) left uncommitted -- a red checkpoint is "
              f"worse than none. `03-checkpoint.py` has already snapshotted them.")
        return

    message = build_message(paths, suite_detail)

    # --- gate 5: the message itself. CLAUDE.md forbids AI attribution in git
    # history, and no human reads this message before it lands.
    if any(p.search(message) for p in AI_ATTRIBUTION_PATTERNS):
        speak("Auto-commit skipped: the generated message matched an "
              "AI-attribution pattern, which CLAUDE.md forbids in git history. "
              "This is a bug in build_message() -- report it.")
        return

    msg_file = REPO_ROOT / ".claude" / "hooks" / "state" / "autocommit-msg.txt"
    try:
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        msg_file.write_text(message, encoding="utf-8")
    except OSError as exc:
        speak(f"Auto-commit could not write its message file ({exc}); "
              f"{len(paths)} file(s) left uncommitted.")
        return

    # A pathspec commit alone cannot commit an untracked file, and a new file is
    # exactly what a turn most often produces. So stage first, still by explicit
    # pathspec: `git add -- <paths>` can only ever touch the set computed above,
    # so the sweep this hook exists to avoid remains impossible.
    rc, _, stderr = git("add", "--", *paths)
    if rc != 0:
        msg_file.unlink(missing_ok=True)
        speak(f"Auto-commit could not stage its own paths ({stderr[:200]}); "
              f"nothing was committed and the index is unchanged.")
        return

    rc, _, stderr = git("commit", "-F", str(msg_file), "--", *paths)
    msg_file.unlink(missing_ok=True)

    if rc != 0:
        # Leave the index as it was found, or a failed commit strands the paths
        # staged and the next session inherits them as somebody else's work.
        rc_undo, _, undo_err = git("restore", "--staged", "--", *paths)
        index_state = ("the index was left as it was found" if rc_undo == 0
                       else f"WARNING: still staged, could not unstage ({undo_err[:120]})")
        speak(f"Auto-commit FAILED and nothing was committed: {stderr[:300]} -- "
              f"{len(paths)} file(s) still uncommitted and {index_state}.")
        return

    rc_sha, sha, _ = git("rev-parse", "--short", "HEAD")
    speak(f"Checkpoint {sha if rc_sha == 0 else 'HEAD'}: {len(paths)} file(s), "
          f"{suite_detail}. Local only -- nothing pushed. Review happens at the "
          f"PR, over the whole branch.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
