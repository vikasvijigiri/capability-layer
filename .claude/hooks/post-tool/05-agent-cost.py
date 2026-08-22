"""post-tool -- counts Task-tool (agent spawn) invocations.

The Notion "Agentic Workflows (IDE)" spec's §21 grades objective 8 (minimum-
sufficient execution graph) on `tool_calls/task` + `agents_spawned/task`
together. `01-context-cost.py` already counts tool calls; nothing counted
agent spawns, so that half of the pair was asserted but never measured.

Best-effort `subagent_type` breakdown: recorded when the payload carries one,
skipped otherwise -- a dispatch this hook cannot classify is still a real
dispatch and must still increment `calls`.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"Task","tool_input":{"subagent_type":"tester"}}'
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

WATCHED = ("Task",)

STATE = Path(__file__).resolve().parents[1] / "state" / "agent-cost.json"


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"calls": 0, "by_type": {}}


def _save(totals: dict) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(totals), encoding="utf-8")
    except OSError:
        pass  # a reporter that cannot persist still must not break the turn


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if name not in WATCHED:
        return 0

    body = payload.get("tool_input") or {}
    subagent_type = body.get("subagent_type")

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    if subagent_type:
        by_type = totals.setdefault("by_type", {})
        by_type[subagent_type] = by_type.get(subagent_type, 0) + 1
    _save(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
