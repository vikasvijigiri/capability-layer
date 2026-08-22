"""stop-finalization -- records this unit's state, and says so when the chain stops moving.

Behaviour classification: **record state**, and **detect drift**. It writes only
to ignored hook state and prints; it authors nothing, edits nothing, and blocks
nothing.

Why it exists
-------------
Every skill names its successor in prose and nothing makes the handoff happen. A
hook cannot invoke a skill -- `decisions/2026-08-04-hooks-never-name-a-skill.md`
-- so the chain between the two gates runs on the model choosing to continue,
and when it does not, the failure is *silent*: the turn ends, the tree is green,
and a skipped stage is indistinguishable from a stage nothing needed.

This cannot fix that. It makes it loud, which is the most a hook is allowed to
do, and it is a strict improvement over silence.

It names no skill
-----------------
It computes a state key and renders the matching `[state:...]` block from
`.claude/workflow.md`, exactly as `session-start/03-state-report.py` does.
`workflow.md` decides what the key means; `tools/test_hook_registration.py`
fails any hook that hardcodes a skill name.

Never blocks
------------
`post-run/05-docs-gate.py` blocked a turn until a skill ran, deadlocked, and was
deleted on 2026-08-02. Write, report, get out of the way.
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".claude" / "workflow.md"
TAG_RE = r"\[state:{key}\](.*?)\[/state:{key}\]"

# Same guard the auto-commit uses. Anything that fires the whole `post-run` event
# from inside a check would otherwise recurse, and the symptom is a hang.
REENTRY_FLAG = "UAIOS_AUTOCOMMIT_RUNNING"
OPT_OUT = "UAIOS_NO_CHAIN_REPORT"


def speak(text: str) -> None:
    """Same shape every post-run hook here uses to reach the next turn."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": text,
    }}))


def load_chain():
    import importlib.util
    path = REPO_ROOT / "tools" / "chain.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("chain_hook", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def workflow_block(key: str) -> str:
    """What `workflow.md` says about this state, or '' if it says nothing.

    No fallback text here on purpose: a copy would be a second source of truth,
    and a missing tag has to look missing rather than degrade to generic prose.
    """
    try:
        text = WORKFLOW.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = re.search(TAG_RE.format(key=re.escape(key)), text, re.S)
    return m.group(1).strip() if m else ""


def main() -> int:
    if os.environ.get(REENTRY_FLAG) or os.environ.get(OPT_OUT):
        return 0
    load_payload()

    chain = load_chain()
    if chain is None:
        return 0

    try:
        facts = chain.gather(REPO_ROOT)
        verdict = chain.assess(facts["entries"], facts["state"],
                               facts["fingerprint"])
        # Record AFTER assessing, so this turn is judged against the history
        # that preceded it rather than against itself.
        chain.record(facts)
    except Exception:
        # A reporting hook must never break a turn. Silence here is the correct
        # failure: the ledger simply misses an entry.
        return 0

    if verdict["chain"] != "stalled":
        return 0

    # The verdict names its own block. A stall with no plan to tick reads
    # differently from a missed handoff, and telling a reader "a stage finished
    # and its successor was never invoked" when the real cause is an absent plan
    # is how a notice stops being believed.
    block = workflow_block(verdict.get("block", "chain-stalled"))
    if not block:
        return 0
    speak(f"Chain continuity: {verdict['reason']}.\n\n{block}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
