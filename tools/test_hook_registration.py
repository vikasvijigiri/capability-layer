#!/usr/bin/env python3
"""Tests that disk, settings.json and hooks_registry.json agree about hooks.

Why this suite exists
---------------------
`/verify` step 4 has described this exact check in prose since the command was
written, and the drift it describes accumulated anyway:

- `session-start/02-bootstrap-docs.py` was in the registry, on disk, and NOT in
  `settings.json` — so the hook that injects the knowledge docs into session
  context **never fired in a real session**. CLAUDE.md's "six files carry state
  between sessions" was describing a capability that was not wired.
- `post-run/05-docs-gate.py` and `pre-commit/05-docs-required.py` were wired and
  on disk but absent from the registry, so the file documenting intent disagreed
  with the file that fires.

A check a human is asked to run by hand is a check that eventually is not run.
Three directions are asserted here, because a hook can be invisible in three
different ways and each is silent:

1. On disk but not in settings.json  -> never fires.
2. In settings.json but not on disk  -> fires and errors, or silently no-ops.
3. On disk but not in the registry   -> fires, but nothing documents why.

Run: python tools/test_hook_registration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / ".claude" / "hooks"
SETTINGS = ROOT / ".claude" / "settings.json"
REGISTRY = HOOKS / "hooks_registry.json"

# Directories under .claude/hooks/ that hold no hook scripts.
NON_EVENT_DIRS = {"state", "__pycache__"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def rel(path: str) -> str:
    """Normalise any way a hook path is written down to `<event>/<script>.py`."""
    path = path.replace("\\", "/").rstrip('"')
    marker = ".claude/hooks/"
    if marker in path:
        path = path.split(marker, 1)[1]
    return path.strip('" ')


# --- gather the three views -------------------------------------------------

on_disk = {
    f"{d.name}/{f.name}"
    for d in HOOKS.iterdir()
    if d.is_dir() and d.name not in NON_EVENT_DIRS
    for f in d.iterdir()
    if f.suffix == ".py"
}

settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
wired: set[str] = set()
for blocks in settings.get("hooks", {}).values():
    for block in blocks:
        for hook in block.get("hooks", []):
            cmd = hook.get("command", "")
            if ".claude/hooks/" in cmd:
                wired.add(rel(cmd.split()[-1] if " " in cmd else cmd))

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["events"]
declared = {rel(s) for e in registry.values() for s in e["subscribers"]}

# Events with no `claude_code_event` have no lifecycle trigger and are fired by
# hand through tools/run_hook.py. Their scripts are exempt from direction 1.
manual_only = {
    rel(s)
    for e in registry.values()
    if not e.get("claude_code_event")
    for s in e["subscribers"]
}

print(f"{len(on_disk)} scripts on disk, {len(wired)} wired, {len(declared)} declared")
print()

# --- direction 1: on disk, not wired ---------------------------------------

unwired = sorted(on_disk - wired - manual_only)
check("every hook on disk is wired in settings.json", not unwired,
      f"never fires: {', '.join(unwired)}")

# --- direction 2: wired, not on disk ---------------------------------------

phantom = sorted(wired - on_disk)
check("every hook wired in settings.json exists on disk", not phantom,
      f"registered but missing: {', '.join(phantom)}")

# --- direction 3: on disk, not declared ------------------------------------

undocumented = sorted(on_disk - declared)
check("every hook on disk is declared in hooks_registry.json", not undocumented,
      f"undocumented: {', '.join(undocumented)}")

stale = sorted(declared - on_disk)
check("every hook declared in hooks_registry.json exists on disk", not stale,
      f"declared but missing: {', '.join(stale)}")

# --- every event directory is a registry event ------------------------------

event_dirs = {d.name for d in HOOKS.iterdir()
              if d.is_dir() and d.name not in NON_EVENT_DIRS}
unregistered_dirs = sorted(event_dirs - set(registry))
check("every hook event directory has a registry entry", not unregistered_dirs,
      f"no entry: {', '.join(unregistered_dirs)}")

empty_events = sorted(k for k, v in registry.items() if not v.get("subscribers"))
check("no registry event has an empty subscriber list", not empty_events,
      f"empty: {', '.join(empty_events)}")

# --- direction 5: globally wired, but is it actually wired? -----------------
#
# `global-session-start/01-layer-bootstrap.py` is deliberately absent from this
# repo's settings.json -- a project hook only fires inside its own project, and
# this one exists to reach every OTHER repo. So directions 1 and 2 cannot see it
# at all, and it would sit on disk firing nowhere with every check green. That is
# the "silently invisible" failure this suite was written for, one level up.
#
# Skipped with a spoken reason where there is no ~/.claude/settings.json, which
# is CI. Locally it is the only thing asserting the wiring exists.

GLOBALLY_WIRED = {"global-session-start/01-layer-bootstrap.py"}

global_settings = Path.home() / ".claude" / "settings.json"
if not global_settings.is_file():
    print(f"SKIP: no {global_settings} -- global hook wiring unchecked "
          f"({', '.join(sorted(GLOBALLY_WIRED))})")
else:
    try:
        gs = json.loads(global_settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        gs = {}
        check("~/.claude/settings.json parses", False, str(exc))
    global_wired = {
        rel(hook.get("command", "").split()[-1])
        for blocks in gs.get("hooks", {}).values()
        for block in blocks
        for hook in block.get("hooks", [])
        if ".claude/hooks/" in hook.get("command", "")
    }
    for name in sorted(GLOBALLY_WIRED):
        check(f"'{name}' is wired in ~/.claude/settings.json",
              name in global_wired,
              "on disk and declared, but fires in no session anywhere")
        check(f"'{name}' is not ALSO wired in this repo's settings.json",
              name not in wired,
              "wired both globally and per-project -- it would run twice here")
        check(f"'{name}' exists on disk", name in on_disk,
              "~/.claude/settings.json names a file that is not here")

# --- the manual-only exemption must be deliberate, not a typo ---------------

for name, entry in sorted(registry.items()):
    if entry.get("claude_code_event"):
        continue
    check(f"manual-only event '{name}' says why it is unwired",
          bool(entry.get("_note")),
          "no _note explaining the absent claude_code_event")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All hook-registration tests passed ({len(on_disk)} hooks, "
      f"{len(event_dirs)} events)")
