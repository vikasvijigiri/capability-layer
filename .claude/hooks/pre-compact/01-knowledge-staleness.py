"""pre-compact -- names `knowledge-manager` when the session is about to forget.

Fires on `PreCompact`, immediately before the context window is compacted.

Why this event and not a Stop gate
----------------------------------
`CLAUDE.md` states plainly that **nothing watches the knowledge docs any more**.
The staleness warner, the Stop gate and the commit gate were all deleted on
2026-08-02 -- the Stop gate because it BLOCKED a turn until a skill ran and
deadlocked, which is why this one only ever speaks.

`Stop` was also the wrong moment. It fires after every turn, so a reminder there
is either constant noise or thresholded into irrelevance. `PreCompact` fires
exactly once per compaction, and compaction is the event that destroys the very
thing `HANDOFF.md` exists to preserve: the session's own memory of what it was
doing. A reminder is worth most at the last moment it can still be acted on.

What it measures
----------------
Commits since the last one that touched a knowledge doc, plus whether the
worktree is dirty. Not "was a skill invoked" -- a hook sees tool calls, not
skills, which is the same limit `07-layer-drift.py` documents and the reason
that hook makes the skill record its own sweep.

Deliberately NOT gated on file count. One commit that lands a subsystem matters
more than nine that fix typos, and the hook cannot tell them apart; the number it
reports is a prompt to look, not a verdict.

Never blocks, and speaks only when there is something to say. `PreCompact`
supports the `decision: block` pattern -- this hook does not use it, on the
argument that a compaction refused is a session wedged.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

# The docs whose whole purpose is surviving a context boundary. `TASK.md` and
# `PLAN.md` are current-state files that a turn may legitimately leave alone;
# these three are the history, and a compaction with none of them touched is a
# session about to lose what it did.
KNOWLEDGE_DOCS = ("LOG.md", "HANDOFF.md", "ISSUES.md")

# Below this, a nudge is noise -- a two-commit session has nothing to hand off
# that `git log` does not already carry.
MIN_COMMITS = 3


def git(*args):
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def commits_since_docs():
    """(count, last_doc_sha). Counts commits after the last knowledge-doc write."""
    last = git("log", "-1", "--format=%H", "--", *KNOWLEDGE_DOCS)
    if not last:
        # No doc has ever been written; count the whole history, capped by the
        # caller's threshold anyway.
        total = git("rev-list", "--count", "HEAD")
        return (int(total) if total.isdigit() else 0), ""
    rng = git("rev-list", "--count", f"{last}..HEAD")
    return (int(rng) if rng.isdigit() else 0), last[:7]


def main():
    if not (REPO_ROOT / ".git").exists():
        return
    payload = load_payload()
    # `trigger` is "auto" or "manual"; both are worth speaking on, but a manual
    # compaction means the user is already curating context deliberately.
    trigger = (payload.get("trigger") or "").lower()

    count, last_sha = commits_since_docs()
    dirty = len([ln for ln in git("status", "--porcelain").splitlines() if ln.strip()])

    if count < MIN_COMMITS:
        return

    where = f"since `{last_sha}`" if last_sha else "in this repo's whole history"
    lines = [
        f"**{count} commit(s) {where} with no write to "
        f"{', '.join('`' + d + '`' for d in KNOWLEDGE_DOCS)}.**",
        "",
        "Context is about to be compacted, which is the boundary those files "
        "exist to survive. Nothing else watches them — the Stop gate that used "
        "to was deleted on 2026-08-02 after it deadlocked.",
        "",
        "`knowledge-manager` owns them. Invoking it now costs one turn; not "
        "invoking it costs whatever this session knew and did not write down.",
    ]
    if dirty:
        lines.insert(1, f"The worktree also has {dirty} uncommitted path(s).")
    if trigger == "manual":
        lines.append("")
        lines.append("(Manual compaction — you may already be curating this.)")

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreCompact",
        "additionalContext": "pre-compact:\n" + "\n".join(lines),
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
