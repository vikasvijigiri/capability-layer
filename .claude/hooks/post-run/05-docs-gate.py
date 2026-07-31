"""post-run -- refuses to end a turn that left substantial work unrecorded.

Why this exists
---------------
`pre-run/04-docs-staleness.py` beeps at the start of a turn. It cannot do more:
a hook is a subprocess with no tool access, so it can never invoke
`knowledge-manager` itself. Nothing connects the warning to the action, and the
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
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

KNOWLEDGE_DOCS = {"LOG.md", "HANDOFF.md", "TASK.md", "PLAN.md", "MEMORY.md", "ISSUES.md"}

# Higher than the pre-run nudge's threshold of 3. The nudge is cheap and should
# fire early and often; a block is expensive and must be rare enough that
# hitting one still means something.
MIN_FILES = 10


def changed_files():
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            out.append(path)
    return out


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

    newest = 0.0
    for rel in work:
        try:
            newest = max(newest, (REPO_ROOT / rel).stat().st_mtime)
        except OSError:
            continue
    if not newest:
        return

    behind = []
    for doc in ("LOG.md", "HANDOFF.md"):
        try:
            if (REPO_ROOT / doc).stat().st_mtime < newest:
                behind.append(doc)
        except OSError:
            behind.append(doc)
    if not behind:
        return

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"{len(work)} files changed and {' and '.join(behind)} "
            f"{'are' if len(behind) > 1 else 'is'} older than the newest of them. "
            "Invoke `knowledge-manager` to record this unit of work before ending "
            "the turn -- it owns these files and nothing writes them automatically. "
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
