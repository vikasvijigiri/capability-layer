"""post-tool -- counts human-gate invocations (`AskUserQuestion`, `ExitPlanMode`).

Objective 1 ("ask only when the system genuinely cannot proceed safely or
correctly") has had a structural instrument (`test_process_router.py`'s
two-gate ownership assertions) but no live rate -- nothing counted how often
either gate actually fires in a real session. `.claude/operating.md` names
both as the layer's two approval gates, each with its own tool: Gate 1
`ExitPlanMode`, Gate 2 `AskUserQuestion`. One hook with a `by_tool`
breakdown answers "how often did either gate fire" without forcing a caller
to sum two files, mirroring `05-agent-cost.py`'s `by_type` shape.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"ExitPlanMode","tool_input":{}}'
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

WATCHED = ("AskUserQuestion", "ExitPlanMode")

STATE = Path(__file__).resolve().parents[1] / "state" / "human-cost.json"


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


def main() -> int:
    payload = load_payload() or {}
    name = payload.get("tool_name") or ""
    if name not in WATCHED:
        return 0

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    by_tool = totals.setdefault("by_tool", {})
    by_tool[name] = by_tool.get(name, 0) + 1
    _save(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
