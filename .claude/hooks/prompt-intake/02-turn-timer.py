"""prompt-intake -- records this turn's start time, for `09-telemetry.py`'s
`turn_latency_seconds` (Notion spec §21's `latency` field, objective 6).

Fires on every `UserPromptSubmit`, before `01-entry-classifier.py`'s own
routing work. One active turn at a time, so this overwrites the state file
rather than accumulating -- mirrors `01-entry-classifier.py`'s own posture of
firing once per turn with no history kept.

Fire it directly:

    python tools/run_hook.py user-prompt '{}'
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from _hooklib import load_payload
except Exception:  # pragma: no cover - a guard that cannot load must not wedge
    sys.exit(0)

STATE = Path(__file__).resolve().parents[1] / "state" / "turn-timer.json"


def main() -> int:
    load_payload()  # drains stdin/HOOK_PAYLOAD per the shared contract; unused
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps({"started_at": time.time()}), encoding="utf-8")
    except OSError:
        pass  # a reporter that cannot persist still must not break the turn
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
