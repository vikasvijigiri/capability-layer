#!/usr/bin/env python3
"""Every tracked .json file parses, and the ones that steer the harness are sane.

Why this is a lint check and not a test suite
---------------------------------------------
`.claude/settings.json` is the only file that decides which hooks fire. A stray
comma in it does not raise anywhere -- Claude Code reads it, fails to parse, and
the entire hook layer silently stops existing. That is the worst failure mode in
this repo: identical, from the inside, to everything working.

`.mcp.json` fails the same way for MCP servers, and `hooks_registry.json` and
`project-checks.json` are read by code that catches `JSONDecodeError` and falls
back to `{}` -- which is correct behaviour and completely silent.

So the check is cheap, the failure is catastrophic, and nothing else looks.

It lives inside `.claude/hooks/` rather than beside a test suite because it is
part of the hook layer: it validates only `.claude/` files, and `.claude/` is the
whole portable unit. Moved here on 2026-08-04 when the repo-root `tools/`
directory was deleted -- of everything in there, this was the only file the hooks
could not do without, being the one guard on their own wiring.

Run: python .claude/hooks/check_config_json.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# `.claude/hooks/check_config_json.py` -> repo root is two levels up. It was one
# level while this lived in `tools/`; getting this wrong makes every path below
# resolve inside `.claude/`, where `git ls-files` finds nothing and the check
# passes vacuously.
ROOT = Path(__file__).resolve().parents[2]

# Files whose *shape* matters, beyond parsing. Each maps to the key that must be
# present -- a settings.json that parses but has no `hooks` block is a file that
# turned every hook off without saying so.
SHAPE = {
    ".claude/settings.json": "hooks",
    ".claude/hooks/hooks_registry.json": "events",
}

# Every hook event Claude Code actually emits, from the official hooks reference
# (fetched 2026-08-04). A hook registered under a name that is not in this set is
# never called, and NOTHING says so -- settings.json parses, the file is on disk,
# `test_hook_registration.py` sees it wired, and the hook simply never runs. That
# is this repo's worst failure mode and no check looked for it.
#
# `hooks_registry.json` is validated against the same set. It was the file this
# audit flagged as a third source of truth with no schema; a generic JSON Schema
# would have restated what `test_hook_registration.py` already asserts, whereas
# a misspelt event name is the one error neither of them could catch.
#
# Keep this list in sync with the docs rather than with what we happen to use --
# an event missing from here would fail a correct registration.
CANONICAL_EVENTS = {
    "SessionStart", "Setup", "SessionEnd",
    "UserPromptSubmit", "UserPromptExpansion", "Stop", "StopFailure",
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "PostToolBatch",
    "PermissionRequest", "PermissionDenied",
    "SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted",
    "TeammateIdle",
    "FileChanged", "CwdChanged", "DirectoryAdded", "InstructionsLoaded",
    "ConfigChange",
    "WorktreeCreate", "WorktreeRemove",
    "PreCompact", "PostCompact",
    "Elicitation", "ElicitationResult",
    "MessageDisplay", "Notification",
}

failures: list[str] = []


def tracked_json():
    try:
        out = subprocess.run(["git", "ls-files", "*.json"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*.json")
                      if ".git" not in p.parts and "__pycache__" not in p.parts)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


paths = tracked_json()
if not paths:
    print("no tracked .json files found -- nothing to check")
    sys.exit(0)

for rel in paths:
    target = ROOT / rel
    if not target.is_file():
        continue
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {rel} does not parse -- line {exc.lineno} col {exc.colno}: {exc.msg}")
        failures.append(rel)
        continue
    except OSError as exc:
        print(f"FAIL: {rel} could not be read -- {exc}")
        failures.append(rel)
        continue

    required = SHAPE.get(rel)
    if required and (not isinstance(data, dict) or required not in data):
        print(f"FAIL: {rel} parses but has no top-level `{required}` key")
        failures.append(rel)
        continue

    print(f"OK: {rel}")

# settings.json naming a hook that is not on disk makes python exit 2, which on
# PreToolUse reads as `deny` -- every Bash call in the session fails. It happened
# on 2026-08-02. test_hook_registration.py asserts this too; it is repeated here
# because this file is the one that runs as a lint check on every commit.
settings = ROOT / ".claude/settings.json"
if settings.is_file():
    try:
        blocks = json.loads(settings.read_text(encoding="utf-8")).get("hooks", {})
    except json.JSONDecodeError:
        blocks = {}
    for event_blocks in blocks.values():
        for block in event_blocks:
            for hook in block.get("hooks", []):
                cmd = hook.get("command", "")
                if ".claude/hooks/" not in cmd:
                    continue
                rel = ".claude/hooks/" + cmd.split(".claude/hooks/", 1)[1].rstrip('"')
                if not (ROOT / rel).is_file():
                    print(f"FAIL: settings.json registers {rel}, which is not on disk "
                          f"-- python exits 2 and PreToolUse reads that as deny")
                    failures.append(rel)

# --- every event name is one Claude Code actually emits ---------------------

if settings.is_file():
    try:
        events = json.loads(settings.read_text(encoding="utf-8")).get("hooks", {})
    except json.JSONDecodeError:
        events = {}
    for name in events:
        if name not in CANONICAL_EVENTS:
            print(f"FAIL: settings.json registers hooks under `{name}`, which is "
                  f"not an event Claude Code emits -- they would never fire, "
                  f"silently")
            failures.append(f"settings.json:{name}")

registry = ROOT / ".claude/hooks/hooks_registry.json"
if registry.is_file():
    try:
        reg = json.loads(registry.read_text(encoding="utf-8")).get("events", {})
    except json.JSONDecodeError:
        reg = {}
    for event, entry in reg.items():
        declared = (entry or {}).get("claude_code_event")
        if not declared:
            continue  # manual-only; test_hook_registration.py demands a _note
        # Entries read "PreToolUse (Bash|PowerShell)" -- the matcher is
        # documentation, the event name is the part before it.
        base = declared.split("(")[0].strip()
        if base not in CANONICAL_EVENTS:
            print(f"FAIL: hooks_registry.json event `{event}` claims "
                  f"`{declared}`, which is not an event Claude Code emits")
            failures.append(f"hooks_registry.json:{event}")

print()
if failures:
    print(f"{len(failures)} problem(s): {', '.join(failures)}")
    sys.exit(1)
print(f"All {len(paths)} config JSON files valid, every event name canonical")
