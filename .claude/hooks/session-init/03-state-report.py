"""session-init -- reports what the repo's state is, and lets workflow.md say
what that state means.

Fires on SessionStart, which covers a fresh start, a `--resume`, and the restart
after a compaction. Compaction is the case that matters most: it destroys the
session's own memory of what it was doing, which is precisely what `HANDOFF.md`
exists to survive.

Why this hook contains NO skill name
------------------------------------
Measuring "the knowledge docs are 14 commits behind" is deterministic and only a
hook can do it reliably. Deciding what that fact *means* is a routing decision,
and `.claude/workflow.md` already owns routing -- it is the file that says which
skill owns which stage.

So this hook resolves state and then renders whatever `workflow.md` says under a
matching `[state:<key>]` block. It is a measurer and a template renderer. Grep it
for the name of any skill and you will find none; delete every skill and it still
runs. Three hooks carried skill names as string literals until 2026-08-04, and
pointing one at a fabricated skill passed every suite -- that is the coupling this
shape does not have.

The pattern is taken from mindfold-ai/Trellis, whose per-turn hook pulls its text
exclusively from `workflow.md` tag blocks and keeps no fallback copy in the
script, so a missing tag shows up as a visibly generic line instead of being
silently masked. The compact/resume detection and the fail-open exit are from
pedrohcgs/claude-code-my-workflow.

No state file, deliberately
---------------------------
An earlier drift counter kept its own JSON marker and produced three separate
bugs in one day: an untracked path no SHA could mask, a volume counter that
rebuilt from the same uncommitted files every turn, and a recorded path that
outlived the rule suppressing it. Every one was the marker disagreeing with git.

So this measures against git alone. "Changed on this branch" is `merge-base..HEAD`
plus the worktree, which is self-scoping: landing the branch resets it with no
bookkeeping. There is nothing to clear and nothing to go stale.

Silent when there is nothing to say, and never blocks.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows default codepage is cp1252 and this repo's own gotcha list leads with
# it: the block below prints `—`, and an unconfigured stream raises
# UnicodeEncodeError, which in a hook presents as silence.
if sys.platform.startswith("win"):
    for _name in ("stdout", "stderr"):
        _s = getattr(sys, _name, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".claude" / "workflow.md"

# The history files, as opposed to current-state files. A turn may legitimately
# leave `TASK.md` alone; these three are the record, and a session
# that ends without touching one of them has left nothing behind.
HISTORY_DOCS = ("LOG.md", "HANDOFF.md", "ISSUES.md")

# Below this a report is noise. Two commits have nothing to hand off that
# `git log` does not already carry.
MIN_COMMITS = 3

# Set to skip the report for one session. Trellis offers the same escape hatch as
# a prompt keyword; SessionStart has no prompt to read, so it is an env var.
OPT_OUT = "UAIOS_NO_STATE_REPORT"

# `[state:<key>]` ... `[/state:<key>]` in workflow.md. Same shape as Trellis's
# `[workflow-state:STATUS]`.
TAG_RE = r"\[state:{key}\]\s*\n(.*?)\n\s*\[/state:{key}\]"


def git(*args: str) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def base_commit() -> str:
    """Where this branch started, or "" when there is no branch point.

    Refs are tried in order because assuming `main` exists is wrong often enough
    to matter -- this repo has only `master`, so a hardcoded `main` made
    `merge-base` return empty and every count silently read 0.

    **Returns "" on the default branch, and the fallback to the root commit is
    gone.** That fallback was a real defect: on `master` every candidate ref is
    skipped as self-comparison, execution reached the root commit, and the hook
    reported the entire 66-commit history as "changed on this branch" -- so the
    branch-scoped state fired permanently on the one branch where everything has
    already landed. There is no branch point on the default branch; saying so is
    the honest answer, and the caller drops the branch-scoped states.
    """
    head = git("rev-parse", "--abbrev-ref", "HEAD")
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        # Compare the final path segment, not a suffix: `endswith` let a branch
        # called `er` alias `master`.
        if ref.rsplit("/", 1)[-1] == head:
            continue
        if not git("rev-parse", "--verify", "--quiet", ref):
            continue
        mb = git("merge-base", ref, "HEAD")
        if mb:
            return mb
    return ""


def counts() -> dict:
    # "" means HEAD *is* the default branch, so nothing is branch-scoped. The
    # branch-scoped keys are then None rather than 0: absent and zero are
    # different facts, and collapsing them is what made the old fallback report
    # the whole history as if it were one branch's work.
    base = base_commit()

    last_doc = git("log", "-1", "--format=%H", "--", *HISTORY_DOCS)
    if last_doc:
        n = git("rev-list", "--count", f"{last_doc}..HEAD")
    else:
        n = git("rev-list", "--count", "HEAD")

    dirty_layer = [ln for ln in git("status", "--porcelain", "--", ".claude").splitlines()
                   if ln.strip()]
    dirty = [ln for ln in git("status", "--porcelain").splitlines() if ln.strip()]

    layer_files = None
    commits_on_branch = None
    if base:
        # Only paths that STILL EXIST. The raw branch diff counts every path ever
        # touched, and on a branch that replaced the layer that is dominated by
        # deletions -- 267 paths of which 45 survive reads as catastrophic drift
        # when it means "this branch rewrote the layer, once". A deleted file
        # needs no sweep; the actionable set is what a reader could still open.
        rng = f"{base}..HEAD"
        layer = [ln for ln in git("diff", "--name-only", rng, "--", ".claude").splitlines()
                 if ln.strip() and (REPO_ROOT / ln.strip()).exists()]
        layer_files = len({*layer, *(x[3:].strip() for x in dirty_layer)})
        commits_on_branch = int(git("rev-list", "--count", rng) or 0)

    return {
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "on_default_branch": not base,
        "commits_on_branch": commits_on_branch,
        "since_history_doc": int(n or 0),
        "last_doc_sha": last_doc[:8],
        "layer_files": layer_files,
        "uncommitted": len(dirty),
        # Zero remotes means committed work has nowhere to go: no push, no PR,
        # and the merge queue is a configuration nobody has ever exercised. Read
        # from git like everything else here, so there is no flag to clear when
        # a remote is finally added.
        "remotes": len([ln for ln in git("remote").splitlines() if ln.strip()]),
    }


def workflow_block(key: str) -> str:
    """What `workflow.md` says about this state, or '' if it says nothing.

    No fallback text lives here on purpose. A missing tag has to look missing --
    a copy in this file would be a second source of truth that drifts, which is
    the whole reason the skill names came out of the hooks.
    """
    try:
        text = WORKFLOW.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = re.search(TAG_RE.format(key=re.escape(key)), text, re.S)
    return m.group(1).strip() if m else ""


def main() -> int:
    if os.environ.get(OPT_OUT):
        return 0
    payload = load_payload()
    # "compact" and "resume" mean the session lost its own memory. pedrohcgs's
    # restore hook keys on exactly this field.
    source = (payload.get("source") or "").lower()

    c = counts()
    states = []
    if c["since_history_doc"] >= MIN_COMMITS:
        states.append("docs-stale")
    # `layer_files` is None on the default branch, where there is no branch point
    # and so nothing is "unreviewed on this branch". `>= 8` against None raises
    # under the module's own fail-open, which would have made the whole report
    # vanish on `master` rather than merely be wrong.
    if c["layer_files"] is not None and c["layer_files"] >= 8:
        # "unreviewed", not "drifted": this is branch-scoped, so it measures what
        # review has not yet seen rather than decay since some marker.
        states.append("layer-unreviewed")
    # Committed work and nowhere to send it. Not reported on the default branch
    # or on an empty branch: a remote is premature until something exists that
    # would go through a PR, and saying so earlier trains people to ignore it.
    if c["remotes"] == 0 and (c["commits_on_branch"] or 0) >= 1:
        states.append("no-remote")
    if not states:
        return 0

    head = "state report:"
    # Past tense by lookup, not by appending "d" -- that produced "compactd".
    past = {"compact": "compacted", "resume": "resumed"}.get(source)
    if past:
        head = f"state report (session {past} -- its own memory of this work is gone):"

    branch = c["branch"] + (" (default branch -- nothing is branch-scoped)"
                            if c["on_default_branch"] else "")
    lines = [
        head,
        f"  branch                        {branch}",
        f"  commits since {'/'.join(HISTORY_DOCS)} changed   {c['since_history_doc']}"
        + (f" (last at {c['last_doc_sha']})" if c["last_doc_sha"] else ""),
        f"  uncommitted paths             {c['uncommitted']}",
    ]
    # Branch-scoped rows only where a branch point exists.
    if not c["on_default_branch"]:
        lines[1:1] = [
            f"  commits on this branch        {c['commits_on_branch']}",
            f"  .claude/ files changed, extant {c['layer_files']}",
        ]
    for key in states:
        block = workflow_block(key)
        lines.append("")
        if block:
            lines.append(block)
        else:
            lines.append(f"`.claude/workflow.md` has no `[state:{key}]` block -- "
                         f"add one, or read the file for what this state needs.")

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open. A hook that raises can wedge a session, and this one only
        # ever reports.
        sys.exit(0)
