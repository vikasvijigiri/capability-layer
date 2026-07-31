"""pre-run -- warns when uncommitted work is not reflected in LOG.md / HANDOFF.md.

Why this exists
---------------
`post-run/04-docs-sync.py` already checks doc staleness, and it could not catch
this repo's own work for three independent reasons:

1. It emits `{"systemMessage": ...}`, which renders in the user's UI and never
   enters the model's context. The model was never told.
2. It runs on `Stop` -- after the turn is over, when acting is no longer
   possible without a new turn.
3. Its `noise_dirs` contains `.claude`, so `os.walk` skips the entire capability
   layer. In a repo that *is* a `.claude` layer, that is nearly every file: on
   2026-07-31, 28 of 29 uncommitted files were under `.claude/` and the check
   saw none of them.

This hook fixes the channel and the timing. `UserPromptSubmit` is the one event
whose `additionalContext` is injected straight into the turn -- the same
mechanism that makes `02-capability-router.py` and `03-task-brief-nudge.py`
actually land -- and it fires at the start of a turn, while there is still a turn
left to act in.

It does not replace `post-run/04-docs-sync.py`. That hook keeps its `Stop`-side
`decision: block` rule for a new decision record, which is a genuine gate; this
one is a passive notice and must stay passive. Escalating a per-turn nudge to a
block would just retrain the model to ignore blocks.

Scope, by design
----------------
Git and mtime answer different questions, and this hook needs both:

- **Git decides what changed.** A checkout, a branch switch or a tool that
  rewrites a file without changing it all move mtimes, so mtime alone would nag
  falsely. `git status --porcelain` answers "is there uncommitted work here".
- **mtime decides whether the doc is behind it.** Git cannot order changes
  within a working tree -- to git, a file edited an hour ago and one edited a
  second ago are both just "modified".

The first version of this hook used git alone and asked "is LOG.md among the
changed files?". That was wrong in a way that made it silent exactly when it
mattered: once LOG.md was edited once and left uncommitted, it stayed in the
changed set forever, so the hook went quiet for the rest of the session while
work piled up behind it. "Touched at some point" is not "touched for this unit
of work". Comparing mtimes fixes it -- a source file modified *after* the last
LOG.md entry means the log is behind.

Never blocks. Fails open -- any error means no context is injected and the turn
proceeds exactly as it would have.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

# The knowledge docs themselves. Changes to these are the *fix*, not the problem,
# so they never count as work needing to be recorded.
KNOWLEDGE_DOCS = {"LOG.md", "HANDOFF.md", "TASK.md", "PLAN.md", "MEMORY.md", "ISSUES.md"}

# Below this, a change is plausibly a one-line fix that no one wants logged.
# High enough that routine edits stay quiet, low enough that a real unit of work
# never slips past.
MIN_FILES_TO_REPORT = 3


def _git(*args):
    """Run a git command, returning stdout or None if git cannot answer."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    return proc.stdout if proc.returncode == 0 else None


def changed_files():
    """Repo-relative paths with uncommitted changes, or None if git cannot answer."""
    out = _git("status", "--porcelain")
    if out is None:
        return None

    paths = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        # Renames arrive as "old -> new"; the new path is what exists now.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            paths.append(path)
    return paths


def head_files():
    """Paths touched by the most recent commit, or [] if git cannot answer."""
    out = _git("show", "--name-only", "--format=", "HEAD")
    return [l.strip() for l in out.splitlines() if l.strip()] if out else []


def unlogged_commit():
    """The last commit changed source but recorded nothing in LOG.md/HANDOFF.md.

    A commit empties `git status`, so the uncommitted-work check below goes
    silent the moment work is committed -- including when it was committed
    *without* a log entry. That is the failure this catches: the staleness gets
    baked into history and becomes invisible, which is silence for the wrong
    reason, the same bug this hook already had once.

    Self-clearing: any later commit that touches LOG.md or HANDOFF.md makes HEAD
    a documented commit and the nudge stops.
    """
    files = head_files()
    if not files:
        return None
    work = [f for f in files if f not in KNOWLEDGE_DOCS]
    docs = [f for f in files if f in ("LOG.md", "HANDOFF.md")]
    if len(work) >= MIN_FILES_TO_REPORT and not docs:
        return work
    return None


def summarize(paths):
    """Group paths into readable areas rather than listing forty files."""
    areas = {}
    for p in paths:
        parts = p.split("/")
        if parts[0] == ".claude" and len(parts) > 1:
            key = f".claude/{parts[1]}"
        elif len(parts) > 1:
            key = f"{parts[0]}/"
        else:
            key = p
        areas[key] = areas.get(key, 0) + 1
    return sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))


def main():
    payload = load_payload()
    prompt = payload.get("prompt") or payload.get("user_input") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return

    paths = changed_files()
    if not paths:
        # Clean tree. That is not proof the docs are current -- it may only mean
        # the work was committed without being recorded.
        work = unlogged_commit()
        if work:
            areas = ", ".join(f"{n} ({c})" for n, c in summarize(work)[:5])
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"Docs staleness (git — the last commit changed {len(work)} files and "
                    f"touched neither LOG.md nor HANDOFF.md):\n"
                    f"- committed: {areas}\n"
                    "`knowledge-manager` owns those files. A commit empties `git status`, "
                    "so this is the only point at which an unrecorded commit is still "
                    "visible. Ignore if that commit was deliberately not worth logging."
                ),
            }}))
        return

    work = [p for p in paths if p not in KNOWLEDGE_DOCS]
    if len(work) < MIN_FILES_TO_REPORT:
        return

    # Newest uncommitted source change. Deleted paths still appear in git status
    # but have no mtime, so they are skipped rather than crashing the hook.
    newest_work = 0.0
    for rel in work:
        try:
            newest_work = max(newest_work, (REPO_ROOT / rel).stat().st_mtime)
        except OSError:
            continue
    if not newest_work:
        return

    # LOG.md is append-per-unit-of-work, HANDOFF.md is overwrite-in-place. Either
    # one older than the newest source change means it does not yet describe the
    # work sitting in the tree.
    behind = []
    for doc in ("LOG.md", "HANDOFF.md"):
        try:
            if (REPO_ROOT / doc).stat().st_mtime < newest_work:
                behind.append(doc)
        except OSError:
            behind.append(doc)  # missing entirely is as behind as it gets
    if not behind:
        return

    areas = ", ".join(f"{name} ({n})" for name, n in summarize(work)[:5])
    lines = [
        f"Docs staleness (git + mtime — {len(work)} uncommitted non-doc files "
        f"changed more recently than {' and '.join(behind)}):",
        f"- changed: {areas}",
        f"- behind the work: {', '.join(behind)}",
        "`knowledge-manager` owns these files and is the only thing that writes "
        "them — nothing does it automatically. Invoke it when a unit of work "
        "finishes, not at the end of the session. Ignore this if the work is "
        "still mid-flight or too small to record.",
    ]

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
