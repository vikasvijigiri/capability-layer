"""post-tool -- total tool-call counter, every tool name, not a slice of them.

The Notion "Agentic Workflows (IDE)" spec's §21 grades objective 4 (minimal
API/tool/MCP calls) on `tool_calls`/`api_call_count`. `01-context-cost.py`,
`04-read-cost.py` and `05-agent-cost.py` each watch one narrow slice
(Bash|PowerShell, Read, Task) -- `Write`, `Edit`, `Grep`, `Glob`, `WebFetch`,
`WebSearch`, `NotebookEdit`, and every `mcp__*` tool have never been counted
anywhere in this repo. This hook matches `"*"` and counts all of them,
additively -- the narrower counters keep running unchanged, so this total
will be >= their sum, never equal to it.

Duplicate-rate notice (Notion §10, "Anti-Repetition Layer")
-------------------------------------------------------------
`01-context-cost.py` already fingerprints every watched Bash/PowerShell call
and keeps a running `_totals.repeats`/`_totals.calls` in
`state/call-fingerprints.json` -- the exact numbers `tools/bench.py` prints
as "duplicate-operation rate". This hook does not recompute that count; it
reads the same totals and, once the session has enough calls for a rate to
mean anything (>=20, chosen to match `bench.py`'s own render floor) and the
rate has crossed 15% (chosen from this session's own measured baseline of
12%, per `docs/plans/2026-08-21-notion-architecture-merge.md`'s Design D --
a session already running above its own observed norm), prints one notice
per crossing rather than on every call after it, so the reminder does not
become the noise it warns about.

A latch, not a recomputed "was the prior call already over" guess: the rate
is `repeats/calls` and every plain (non-repeat) call only ever holds it or
pulls it down (a bigger denominator, same numerator), so inferring "the
previous call" from the current totals alone cannot tell a real crossing
from a repeat call that arrived after the rate had already fallen back
under threshold on a run of plain calls. The latch in `tool-cost.json`
(`dup_notice_active`) instead records the true fact -- whether the LAST
check already fired -- and resets once the rate drops back at/under
threshold, so it can fire again on a later, later climb.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"mcp__github__get_me","tool_input":{}}'
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from _hooklib import load_payload
except Exception:  # pragma: no cover - a guard that cannot load must not wedge
    sys.exit(0)

STATE = Path(__file__).resolve().parents[1] / "state" / "tool-cost.json"
FINGERPRINT_STATE = Path(__file__).resolve().parents[1] / "state" / "call-fingerprints.json"

MIN_CALLS_FOR_RATE = 20
DUPLICATE_RATE_THRESHOLD = 15


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"calls": 0, "by_tool": {}}


def _save(totals: dict) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(totals), encoding="utf-8")
    except OSError:
        pass  # a reporter that cannot persist still must not break the turn


def _duplicate_rate_notice(totals: dict) -> str:
    """'' unless the shared fingerprint rate just crossed the threshold.

    Mutates `totals["dup_notice_active"]`, the latch -- caller saves it.
    """
    try:
        fp_totals = json.loads(FINGERPRINT_STATE.read_text(encoding="utf-8")).get("_totals") or {}
    except (OSError, ValueError):
        return ""
    calls = int(fp_totals.get("calls", 0))
    repeats = int(fp_totals.get("repeats", 0))
    was_active = bool(totals.get("dup_notice_active", False))
    if calls < MIN_CALLS_FOR_RATE:
        return ""
    pct = repeats * 100 // calls
    if pct <= DUPLICATE_RATE_THRESHOLD:
        totals["dup_notice_active"] = False
        return ""
    totals["dup_notice_active"] = True
    if was_active:
        return ""  # already notified for this climb; wait for a reset first
    return (
        f"[duplicate rate] this session's Bash/PowerShell duplicate-operation "
        f"rate just crossed {DUPLICATE_RATE_THRESHOLD}% ({repeats}/{calls}, "
        f"now {pct}%). A repeat is a call whose answer was already in "
        f"context -- reuse before retrieve."
    )


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if not name:
        return 0

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    by_tool = totals.setdefault("by_tool", {})
    by_tool[name] = by_tool.get(name, 0) + 1

    notice = _duplicate_rate_notice(totals)
    _save(totals)
    if notice:
        print(notice, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
