"""
PostToolUse hook -- global, fires after Edit/Write completes on any file
under .claude/hooks/**/*.py.

Purpose: the same failure class 04-delivery-guard.py's review reminder exists
to patch -- "did you actually verify this" is model judgment, and that judgment
can silently skip testing a hook change before considering it done. A real bug (04-delivery-guard.py's
AI-attribution regex false-positiving on the literal filename "CLAUDE.md",
blocking a legitimate commit) only got caught because testing happened to
occur anyway, not because anything enforced it.

Scope, by design: fires only on Edit/Write targeting .claude/hooks/**/*.py --
not source edits in general elsewhere. A hook bug here silently affects
every run in this repo using the repo's .claude layer, forever, until noticed; an
ordinary source edit already gets whatever review discipline the task at
hand calls for. This file class is uniquely higher blast-radius.

Never blocks -- PostToolUse can't undo the edit anyway, and this is a
reminder, not a gate. Fails open (top-level try/except; any error means no
additionalContext is added).
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402

import json
import os


def is_hook_script(path):
    if not path:
        return False
    normalized = os.path.normpath(path).replace("\\", "/")
    hooks_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    ).replace("\\", "/")
    return normalized.startswith(hooks_dir + "/") and normalized.endswith(".py")


def main():
    try:
        data = _load_payload()
    except Exception:
        return

    if data.get("tool_name") not in ("Edit", "Write"):
        return

    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not is_hook_script(path):
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "Hook self-test nudge: you just edited a global hook script "
                f"({os.path.basename(path)}). Run it directly against a "
                "realistic input before considering this done -- reading the "
                "diff is not enough. A past false-positive regex bug here "
                "only got caught because someone happened to try it anyway; "
                "nothing enforced it."
            ),
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
