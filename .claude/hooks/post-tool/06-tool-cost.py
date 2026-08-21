"""post-tool -- total tool-call counter, every tool name, not a slice of them.

The Notion "Agentic Workflows (IDE)" spec's §21 grades objective 4 (minimal
API/tool/MCP calls) on `tool_calls`/`api_call_count`. `01-context-cost.py`,
`04-read-cost.py` and `05-agent-cost.py` each watch one narrow slice
(Bash|PowerShell, Read, Task) -- `Write`, `Edit`, `Grep`, `Glob`, `WebFetch`,
`WebSearch`, `NotebookEdit`, and every `mcp__*` tool have never been counted
anywhere in this repo. This hook matches `"*"` and counts all of them,
additively -- the narrower counters keep running unchanged, so this total
will be >= their sum, never equal to it.

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
    if not name:
        return 0

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    by_tool = totals.setdefault("by_tool", {})
    by_tool[name] = by_tool.get(name, 0) + 1
    _save(totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
