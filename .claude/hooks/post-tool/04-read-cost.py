"""post-tool -- counts bytes a Read call adds to permanent session context.

Proxy, not the real field
--------------------------
The Notion "Agentic Workflows (IDE)" spec's §21 wants `context_tokens`. No
hook payload in this harness exposes a token count or what the model actually
saw after truncation/line-numbering, so this counts the file-on-disk byte
size of every `Read` target instead. That is a proxy: it can overstate (a
Read the harness truncates) or understate (line-number prefixes the harness
adds). `09-telemetry.py` carries this same caveat in its own docstring rather
than presenting the number as `context_tokens` itself.

Same threshold and shape as `01-context-cost.py:63,102-124` (`WARN_CHARS`,
`_load`/`_save`) -- duplicated rather than imported because each hook must
survive the other being absent, per the module-isolation pattern already used
across `post-tool/`.

Fire it directly:

    python tools/run_hook.py post-tool '{"tool_name":"Read","tool_input":{"file_path":"README.md"}}'
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

# Mirrors 01-context-cost.py:63 -- same distribution, same threshold.
WARN_CHARS = 700

WATCHED = ("Read",)

STATE = Path(__file__).resolve().parents[1] / "state" / "read-cost.json"


def _load() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"calls": 0, "chars": 0}


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
    file_path = str(body.get("file_path") or "")

    size = 0
    if file_path:
        try:
            size = Path(file_path).stat().st_size
        except OSError:
            size = 0  # a nonexistent or unreadable path is not this hook's problem

    totals = _load()
    totals["calls"] = totals.get("calls", 0) + 1
    totals["chars"] = totals.get("chars", 0) + size
    _save(totals)

    if size >= WARN_CHARS:
        tokens = size // 4
        print(
            f"[context cost] that Read added {size:,} bytes (~{tokens:,} tokens) "
            f"to permanent context, re-read on every later request.\n"
            f"  If only part of the file is needed, prefer offset/limit on a "
            f"future Read of the same path.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
