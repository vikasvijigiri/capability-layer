"""post-run -- refuses to end a turn that left substantial work unrecorded.

Why this exists
---------------
`pre-run/04-docs-staleness.py` beeps at the start of a turn. It cannot do more:
a hook is a subprocess with no tool access, so it can never write the docs
itself. Nothing connects the warning to the action, and the
gap was demonstrably not closed by warning harder -- across three consecutive
turns the nudge fired correctly, was read, and was converted into a question to
the user instead of an action.

`Stop` is the one event that can close that gap. Returning `decision: block`
prevents the turn from ending and puts `reason` into the model's context, so the
work cannot be left unrecorded merely by moving on. The hook still does not
invoke the skill -- it removes the option of skipping it.

Scoped deliberately
-------------------
Only fires above MIN_FILES, and only when both LOG.md and HANDOFF.md are behind.
`post-run/04-docs-sync.py` makes the argument this hook obeys: escalating every
rule to a block just trains the model to ignore blocks. A gate that fires on a
two-file change would be noise, and noise is how a gate stops working.

`stop_hook_active` is honoured. Claude Code sets it when a Stop hook has already
blocked once this turn; blocking again on the same turn would loop forever with
no way for the model to satisfy the gate. One block, then get out of the way.

Never blocks on error. Any exception means the turn ends normally.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    KNOWLEDGE_DOCS,
    changed_paths,
    doc_digests,
    load_payload,
    load_turn_marker,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Higher than the pre-run nudge's threshold of 3. The nudge is cheap and should
# fire early and often; a block is expensive and must be rare enough that
# hitting one still means something.
MIN_FILES = 10


def changed_files():
    """Delegates to `_hooklib.changed_paths` so this and `save_turn_marker` agree."""
    return changed_paths(REPO_ROOT)


def main():
    payload = load_payload()

    # Already blocked once this turn -- blocking again cannot be satisfied.
    if payload.get("stop_hook_active"):
        return

    paths = changed_files()
    if not paths:
        return

    work = [p for p in paths if p not in KNOWLEDGE_DOCS]
    if len(work) < MIN_FILES:
        return

    # Did THIS turn write the docs? Compare their content against the snapshot
    # `pre-run/04-docs-staleness.py` takes at UserPromptSubmit.
    #
    # This replaced an mtime comparison ("are the docs older than the newest changed
    # file?") that produced three false blocks on 2026-08-01 alone, every one of them
    # on a turn where the docs had in fact been written. Two independent causes:
    # git's index refresh bumps working-file mtimes during `git add`, so a file could
    # land 13 seconds after a correct write; and a large uncommitted backlog keeps old
    # mtimes forever, so the gate stayed permanently hot. A gate that cries wolf gets
    # clicked through, which is the exact failure it exists to prevent.
    #
    # Content beats timestamps here for the same reason `pre-commit/05-docs-required.py`
    # checks staged *paths* rather than clock values, and has never false-positived.
    before = load_turn_marker()
    now = doc_digests()

    # Did THIS turn add any work? The `work` set above is the whole uncommitted
    # backlog -- a standing condition. Comparing a standing trigger against a
    # per-turn doc check meant that once the backlog passed MIN_FILES, every later
    # turn tripped the gate, including turns that changed nothing. It fired five
    # times in one session on 2026-08-02 and its escape hatch was used three times,
    # which is how a gate stops being read. `save_turn_marker` now records the work
    # set at UserPromptSubmit so the two comparisons are on the same footing.
    #
    # A marker with no `work` key (written before this change) or `work: null` (git
    # could not answer) is not evidence that the turn was idle, so neither excuses
    # it -- the gate keeps its previous behaviour rather than silently going quiet.
    if before is not None and isinstance(before.get("work"), list):
        if sorted(work) == before["work"]:
            return

    if before is None:
        # No snapshot -- first turn of a session, or the UserPromptSubmit hook did not
        # run. Cannot tell recorded from unrecorded, so allow. A missed block is
        # recoverable; a false one teaches the user to ignore this gate.
        return

    behind = [doc for doc in ("LOG.md", "HANDOFF.md")
              if now.get(doc) == before.get(doc)]
    if len(behind) < 2:
        # Either file written this turn counts as recording the work.
        return

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"This turn changed files and {' and '.join(behind)} "
            f"{'were' if len(behind) > 1 else 'was'} not written during it "
            f"({len(work)} files uncommitted in total). "
            "Invoke `knowledge-manager` to record this unit of work in LOG.md and "
            "HANDOFF.md before ending the turn -- it owns these files and nothing "
            "writes them automatically. "
            "No hook can invoke a skill, which is why this is a block rather than "
            "another reminder. If the work is genuinely mid-flight or not worth "
            "recording, say so explicitly and continue; this fires once per turn."
        ),
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
