#!/usr/bin/env python3
"""Check repository hooks against guide/how_to_create_hooks.md invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
CANONICAL_EVENTS = {
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PostToolUseFailure", "Notification", "SubagentStart",
    "SubagentStop", "Stop", "PreCompact", "PostCompact", "FileChanged",
    "CwdChanged", "SessionEnd",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"settings.json is unreadable or invalid: {exc}")

    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        fail("settings.json has no hooks mapping")

    seen: set[Path] = set()
    for event, groups in hooks.items():
        if event not in CANONICAL_EVENTS:
            fail(f"non-canonical event name: {event}")
        if not isinstance(groups, list) or not groups:
            fail(f"{event} has no hook groups")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                fail(f"{event} has a malformed hook group")
            if event in {"PreToolUse", "PostToolUse", "PostToolUseFailure"} and not group.get("matcher"):
                fail(f"{event} group has no narrow matcher")
            for hook in group["hooks"]:
                if hook.get("type") != "command":
                    fail(f"{event} uses unsupported/non-command hook type in this repo")
                command = hook.get("command", "")
                if "$CLAUDE_PROJECT_DIR" not in command:
                    fail(f"{event} command is not rooted at $CLAUDE_PROJECT_DIR")
                match = re.search(r"\.claude/hooks/([^\"']+\.py)", command)
                if not match:
                    fail(f"{event} command does not name a repository hook script")
                assert match is not None
                path = ROOT / ".claude" / "hooks" / Path(match.group(1))
                if not path.is_file():
                    fail(f"registered hook is missing: {path.relative_to(ROOT)}")
                seen.add(path)
                source = path.read_text(encoding="utf-8", errors="replace")
                if "load_payload" not in source:
                    fail(f"hook does not read the event payload: {path.relative_to(ROOT)}")
                if event == "PreToolUse" and "deny(" not in source and "permissionDecision" not in source:
                    fail(f"PreToolUse hook has no visible blocking decision: {path.relative_to(ROOT)}")

    print(f"OK: {len(seen)} registered command hooks follow the hook guide contract")
    print("OK: canonical events, narrow tool matchers, project-rooted commands, payload loading, and PreToolUse decisions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
